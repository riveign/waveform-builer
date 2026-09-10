"""Put a record you own on the shelf into the library.

Shaped after `kiku fix-album` (`metadata/correct.py`): look it up, see the whole
thing before anything is written, then apply. The difference is what the DJ is
confirming. `fix-album` shows "here is what we found, is it right?"; this shows
"here is the tracklist, now tell us the BPMs" — because the AcousticBrainz spike
(spec Research R1) found a BPM for 1 recording in 54. Nobody is going to fill
those in for you.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from kiku.db.models import Track, VinylRelease
from kiku.metadata.models import ReleaseCandidate
from kiku.vinyl.position import parse_position

# Sources that can answer "what is on this record?". Discogs first: it is the
# only one that knows side positions, and Research R2 moved its value from
# enrichment to exactly these catalog facts.
VINYL_SOURCES: tuple[str, ...] = ("discogs", "musicbrainz")


@dataclass
class PreviewRow:
    """One side of the record, as it would land."""

    position_raw: str | None
    side: int | None
    index: int | None
    title: str
    artist: str | None
    duration_sec: float | None
    existing_track_id: int | None = None  # already imported — this is a re-import


@dataclass
class ImportPreview:
    candidate: ReleaseCandidate
    rows: list[PreviewRow] = field(default_factory=list)
    existing_release_id: int | None = None

    @property
    def is_reimport(self) -> bool:
        return self.existing_release_id is not None

    @property
    def new_count(self) -> int:
        return sum(1 for r in self.rows if r.existing_track_id is None)


class NoVinylSource(RuntimeError):
    """No configured source can look a record up right now."""


def _source_or_raise(source_name: str):
    from kiku.metadata.sources import get_source

    src = get_source(source_name)
    if not src.available():
        raise NoVinylSource(
            f"{source_name} isn't set up yet — "
            "`kiku config set discogs.token <TOKEN>` and try again."
        )
    return src


def search_releases(
    album: str,
    artist: str = "",
    *,
    source_name: str = "discogs",
    limit: int = 5,
) -> list[ReleaseCandidate]:
    """Find pressings matching an album name."""
    return _source_or_raise(source_name).search(album, artist, limit=limit)


def fetch_release_url(url: str, *, source_name: str = "discogs") -> ReleaseCandidate | None:
    """Build a candidate straight from a Discogs release URL."""
    return _source_or_raise(source_name).fetch_url(url)


def build_preview(session: Session, candidate: ReleaseCandidate) -> ImportPreview:
    """Show the whole record before a single row is written."""
    existing_release = _find_existing_release(session, candidate)
    preview = ImportPreview(
        candidate=candidate,
        existing_release_id=existing_release.id if existing_release else None,
    )

    by_position: dict[str, Track] = {}
    if existing_release:
        for tr in session.query(Track).filter(Track.vinyl_release_id == existing_release.id):
            if tr.vinyl_position:
                by_position[tr.vinyl_position] = tr

    for rec in candidate.recordings:
        raw = rec.position_raw
        side, index = parse_position(raw)
        if side is None and index is None:
            side, index = rec.disc, rec.position
        existing = by_position.get(raw) if raw else None
        preview.rows.append(
            PreviewRow(
                position_raw=raw,
                side=side,
                index=index,
                title=rec.title,
                artist=rec.artist or candidate.artist,
                duration_sec=(rec.length_ms / 1000.0) if rec.length_ms else None,
                existing_track_id=existing.id if existing else None,
            )
        )
    return preview


def apply_import(
    session: Session,
    candidate: ReleaseCandidate,
    *,
    acquired_on: str | None = None,
    notes: str | None = None,
) -> VinylRelease:
    """Write the pressing and one track row per side position.

    Idempotent by `discogs_release_id`: adding the same record twice updates the
    sides you already have rather than growing a second copy of the shelf.
    """
    from kiku.metadata.sources.discogs import rpm_from_format

    release = _find_existing_release(session, candidate)
    if release is None:
        release = VinylRelease()
        session.add(release)

    if candidate.source == "discogs":
        release.discogs_release_id = candidate.source_id
    elif candidate.source == "musicbrainz":
        release.mb_release_id = candidate.source_id

    release.title = candidate.album
    release.artist = candidate.artist
    release.label = candidate.label
    release.catalog_number = candidate.catalog_number
    release.year = candidate.year
    release.country = candidate.country
    release.format = candidate.format
    release.rpm = rpm_from_format(candidate.format)
    release.cover_url = candidate.cover_url
    if acquired_on:
        release.acquired_on = acquired_on
    if notes:
        release.notes = notes
    session.flush()  # release.id

    preview = build_preview(session, candidate)
    sides: set[int] = set()
    now = datetime.now().isoformat()

    for row in preview.rows:
        track = (
            session.get(Track, row.existing_track_id) if row.existing_track_id is not None else None
        )
        if track is None:
            track = Track(medium="vinyl", enrichment_status="pending")
            session.add(track)

        track.medium = "vinyl"
        track.vinyl_release_id = release.id
        track.vinyl_position = row.position_raw
        track.title = row.title
        track.artist = row.artist
        track.album = candidate.album
        track.label = candidate.label
        track.release_year = candidate.year
        track.disc_number = row.side
        track.track_number = row.index
        # Discogs leaves the duration blank on most 12"s, so never blank out a
        # length the DJ typed by writing None over it.
        if row.duration_sec is not None:
            track.duration_sec = row.duration_sec
        track.mb_recording_id = _mbid_for(candidate, row.position_raw, row.title)
        track.last_synced = now
        if track.enrichment_status is None:
            track.enrichment_status = "pending"
        if row.side:
            sides.add(row.side)

    release.side_count = len(sides) or None
    session.commit()
    return release


def set_manual_bpm_key(
    session: Session,
    track_id: int,
    *,
    bpm: float | None = None,
    key: str | None = None,
    duration_sec: float | None = None,
) -> Track:
    """The DJ types the number. That marker is the top of the provenance ladder.

    `manual` outranks essentia, rekordbox and acousticbrainz, so a later
    enrichment pass can read this and know to leave it alone.
    """
    track = session.get(Track, track_id)
    if track is None:
        raise ValueError(f"No track with id {track_id}")

    if bpm is not None:
        if bpm <= 0 or bpm > 300:
            raise ValueError(f"{bpm} doesn't look like a BPM — expected 1-300")
        track.bpm = float(bpm)
        track.bpm_source = "manual"
    if key is not None and key.strip():
        track.key = key.strip()
        track.key_source = "manual"
    if duration_sec is not None:
        # Discogs leaves the duration blank on most 12"s, and the builder
        # estimates past a blank rather than failing — so a typed length is the
        # difference between an estimated set time and a real one.
        if duration_sec <= 0:
            raise ValueError(f"{duration_sec} isn't a length")
        track.duration_sec = float(duration_sec)
    if track.bpm:
        track.enrichment_status = "manual"
    session.commit()
    return track


def _find_existing_release(session: Session, candidate: ReleaseCandidate) -> VinylRelease | None:
    if candidate.source == "discogs":
        return (
            session.query(VinylRelease)
            .filter(VinylRelease.discogs_release_id == candidate.source_id)
            .first()
        )
    if candidate.source == "musicbrainz":
        return (
            session.query(VinylRelease)
            .filter(VinylRelease.mb_release_id == candidate.source_id)
            .first()
        )
    return None


def _mbid_for(candidate: ReleaseCandidate, position_raw: str | None, title: str) -> str | None:
    """The recording MBID for this side, when the source carried one.

    Discogs never does — the Discogs->MB hop is slice-2 work (Research R3 leaves
    it the highest-value unmeasured question), so this stays NULL for a Discogs
    import and the row simply has no AcousticBrainz key. That is honest, not a gap.
    """
    for rec in candidate.recordings:
        if rec.mbid and ((position_raw and rec.position_raw == position_raw) or rec.title == title):
            return rec.mbid
    return None
