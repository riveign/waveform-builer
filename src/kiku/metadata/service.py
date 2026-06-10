"""Orchestration shared by the fix-album CLI and the albums API.

Resolves which library tracks a correction targets, gathers candidates from the
chosen source (each source has its own lookup mode), and hands back the diff —
without committing anything. Applying stays an explicit, separate step.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from kiku.db.models import Track
from kiku.metadata.album_key import find_album_by_key
from kiku.metadata.correct import build_correction, discover_tracks_for_release
from kiku.metadata.models import CORRECTABLE_FIELDS, ReleaseCandidate, TrackCorrection
from kiku.metadata.sources import get_source
from kiku.metadata.sources.base import LookupUnsupported, SourceUnavailable

logger = logging.getLogger(__name__)


def gather_candidates(
    source_name: str,
    *,
    url: str | None = None,
    album: str | None = None,
    artist: str | None = None,
    track_paths: list[str] | None = None,
    limit: int = 3,
) -> list[ReleaseCandidate]:
    """Fetch release candidates from a source using whichever lookup it supports."""
    source = get_source(source_name)
    if not source.available():
        raise SourceUnavailable(f"Source {source_name!r} is not available (check configuration)")

    if source_name == "tags":
        cand = source.from_paths(track_paths or [])  # type: ignore[attr-defined]
        return [cand] if cand else []

    if url:
        cand = source.fetch_url(url)
        return [cand] if cand else []

    if album:
        return source.search(album, artist or "", limit=limit)

    raise LookupUnsupported(
        f"Source {source_name!r} needs a URL or an album query"
    )


def tracks_for_target(
    session: Session,
    *,
    album_key: str | None = None,
    track_ids: list[int] | None = None,
    like: str | None = None,
    candidate: ReleaseCandidate | None = None,
) -> tuple[list[Track], str | None]:
    """Resolve the set of library tracks a correction will operate on.

    Resolution order:
      - explicit track_ids
      - an existing album_key grouping
      - discovery from a candidate's tracklist (recovers ungrouped albums)
    Returns (tracks, resolved_album_key).
    """
    if track_ids:
        tracks = session.query(Track).filter(Track.id.in_(track_ids)).all()
        return tracks, album_key

    if album_key:
        resolved = find_album_by_key(session, album_key)
        if not resolved:
            return [], album_key
        names, _, _ = resolved
        tracks = session.query(Track).filter(Track.album.in_(names)).all()
        return tracks, album_key

    if candidate is not None:
        tracks = discover_tracks_for_release(session, candidate, like=like)
        return tracks, None

    return [], album_key


def correct_from_source(
    session: Session,
    source_name: str,
    *,
    album_key: str | None = None,
    track_ids: list[int] | None = None,
    url: str | None = None,
    album: str | None = None,
    artist: str | None = None,
    like: str | None = None,
    candidate_index: int = 0,
    fields: tuple[str, ...] = CORRECTABLE_FIELDS,
) -> tuple[ReleaseCandidate | None, list[Track], list[TrackCorrection]]:
    """End-to-end preview: pick target tracks + a candidate, return the diff.

    For URL/tags lookups the candidate is fetched first; for tags the target
    tracks must be known up front (we read their files), so callers pass an
    album_key/track_ids. Returns (candidate, tracks, corrections) — no writes.
    """
    # Determine target tracks early when we need their paths (tags) or grouping.
    pre_tracks, resolved_key = tracks_for_target(
        session, album_key=album_key, track_ids=track_ids
    )

    candidates = gather_candidates(
        source_name,
        url=url,
        album=album,
        artist=artist,
        track_paths=[t.file_path for t in pre_tracks if t.file_path],
        limit=max(3, candidate_index + 1),
    )
    if not candidates:
        return None, pre_tracks, []
    candidate = candidates[min(candidate_index, len(candidates) - 1)]

    # If we didn't already have target tracks, discover them from the candidate.
    tracks = pre_tracks
    if not tracks:
        tracks, resolved_key = tracks_for_target(
            session, like=like, candidate=candidate
        )

    corrections = build_correction(tracks, candidate, fields=fields)
    return candidate, tracks, corrections
