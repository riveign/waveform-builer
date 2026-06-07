"""Build before→after corrections from a source candidate and apply them.

The flow is always: align the DJ's tracks to the source's recordings (reusing
the existing fuzzy title matcher), compute a per-field old→new diff, show it,
then write only the fields the DJ confirmed — and only where the value actually
changes. Nothing here writes without an explicit field allow-list.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from kiku.db.models import AlbumMetadata, Track
from kiku.metadata.models import (
    CORRECTABLE_FIELDS,
    FieldChange,
    RecordingCandidate,
    ReleaseCandidate,
    TrackCorrection,
)
from kiku.musicbrainz.match import match_tracklist, normalize_title

logger = logging.getLogger(__name__)

# Below this title similarity a discovered track is not considered part of the release.
# Discovery scans the whole library, so it must be precise: we use a strict
# edit-distance ratio (not token_set_ratio, which scores a subset title like
# "You" against "Bite the Hand That Feeds You" near-perfect and creates false
# positives). High threshold because the source title and the file title should
# be near-identical for a real member of the release.
DISCOVER_THRESHOLD = 0.85

# Maps a correctable field to (Track attribute, candidate/recording value resolver).
_TRACK_ATTR = {
    "title": "title",
    "artist": "artist",
    "album": "album",
    "label": "label",
    "release_year": "release_year",
    "track_number": "track_number",
    "disc_number": "disc_number",
}


def build_correction(
    db_tracks: list[Track],
    candidate: ReleaseCandidate,
    *,
    fields: tuple[str, ...] = CORRECTABLE_FIELDS,
) -> list[TrackCorrection]:
    """Align tracks to the candidate and produce a per-track field diff."""
    recordings = candidate.recordings
    by_norm_title = {normalize_title(r.title): r for r in recordings}

    mapping = match_tracklist(
        [{"id": t.id, "title": t.title or ""} for t in db_tracks],
        [
            {"position": r.position, "disc": r.disc, "title": r.title}
            for r in recordings
        ],
    )
    track_by_id = {t.id: t for t in db_tracks}

    corrections: list[TrackCorrection] = []
    for m in mapping:
        track = track_by_id.get(m["track_id"])
        if track is None:
            continue
        rec = by_norm_title.get(normalize_title(m.get("mb_title")))
        changes = _changes_for(track, candidate, rec, fields)
        corrections.append(TrackCorrection(
            track_id=track.id,
            matched_title=m.get("mb_title"),
            confidence=float(m.get("confidence", 0.0)),
            changes=changes,
        ))
    return corrections


def _changes_for(
    track: Track,
    candidate: ReleaseCandidate,
    rec: RecordingCandidate | None,
    fields: tuple[str, ...],
) -> list[FieldChange]:
    proposed: dict[str, str | int | None] = {
        "album": candidate.album,
        "label": candidate.label,
        "release_year": candidate.year,
    }
    if rec is not None:
        proposed["title"] = rec.title
        # Per-track artist wins on compilations; else the release artist.
        proposed["artist"] = rec.artist or candidate.artist
        proposed["track_number"] = rec.position
        proposed["disc_number"] = rec.disc
    else:
        # No tracklist match → still allow album-level fields, but not title/order.
        proposed["artist"] = candidate.artist

    changes: list[FieldChange] = []
    for f in fields:
        if f not in proposed:
            continue
        changes.append(FieldChange(
            field=f,
            old=getattr(track, _TRACK_ATTR[f], None),
            new=proposed.get(f),
        ))
    return changes


def discover_tracks_for_release(
    session: Session,
    candidate: ReleaseCandidate,
    *,
    like: str | None = None,
    threshold: float = DISCOVER_THRESHOLD,
) -> list[Track]:
    """Find library tracks belonging to a release even when album/artist are wrong.

    This is the recovery path for releases that never grouped (e.g. master files
    whose side-position leaked into the artist field): match each source
    recording's title against the library by fuzzy similarity. `like` optionally
    scopes the search to a file_path pattern.
    """
    from thefuzz import fuzz

    q = session.query(Track)
    if like:
        q = q.filter(Track.file_path.like(like))
    pool = q.all()
    pool_norm = [(t, normalize_title(t.title)) for t in pool]

    chosen: dict[int, tuple[Track, float]] = {}
    for rec in candidate.recordings:
        rec_norm = normalize_title(rec.title)
        if not rec_norm:
            continue
        best: tuple[Track, float] | None = None
        for t, tn in pool_norm:
            if not tn or t.id in chosen:
                continue
            # token_sort_ratio tolerates word-order differences but, unlike
            # token_set_ratio, does NOT reward subset titles — exactly what
            # cross-library discovery needs to stay precise.
            score = fuzz.token_sort_ratio(rec_norm, tn) / 100.0
            if best is None or score > best[1]:
                best = (t, score)
        if best and best[1] >= threshold:
            chosen[best[0].id] = best
    return [t for t, _ in chosen.values()]


def apply_correction(
    session: Session,
    corrections: list[TrackCorrection],
    *,
    fields: tuple[str, ...],
    candidate: ReleaseCandidate | None = None,
    album_key: str | None = None,
    commit: bool = True,
) -> int:
    """Write the confirmed field changes. Returns the number of tracks touched.

    Only fields in `fields` are written, and only where the change is real
    (new differs from old and is non-empty) — see FieldChange.changed.
    """
    allowed = set(fields)
    touched = 0
    for corr in corrections:
        track = session.get(Track, corr.track_id)
        if track is None:
            continue
        wrote = False
        for change in corr.changes:
            if change.field not in allowed or not change.changed:
                continue
            setattr(track, _TRACK_ATTR[change.field], change.new)
            wrote = True
        if wrote:
            touched += 1

    if candidate is not None and album_key is not None:
        _record_source(session, album_key, candidate)

    if commit:
        session.commit()
    return touched


def _record_source(session: Session, album_key: str, candidate: ReleaseCandidate) -> None:
    md = session.get(AlbumMetadata, album_key)
    if md is None:
        md = AlbumMetadata(
            album_key=album_key,
            album=candidate.album or "",
            album_artist=candidate.artist or "Unknown Artist",
        )
        session.add(md)
    md.source = candidate.source
    md.source_ref = candidate.source_id
    if candidate.source == "musicbrainz":
        md.mb_release_id = candidate.source_id
    md.last_matched_at = datetime.utcnow()
    md.match_status = "applied"
