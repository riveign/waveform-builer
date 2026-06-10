"""The cover-art resolution chain. Never raises to the caller.

Order: disk cache → embedded tags → CAA (only if mb_release_id known) → iTunes →
Deezer → `.missing` sentinel. Every resolved image is cached on disk keyed by
album_key, and the winning source is recorded on AlbumMetadata for UI attribution.
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from kiku.db.models import AlbumMetadata, Track
from kiku.metadata.album_key import find_album_by_key
from kiku.musicbrainz.cover_art import (
    cached_cover_path,
    fetch_front_cover,
    is_cover_known_missing,
    mark_cover_missing,
    store_cover,
)

logger = logging.getLogger(__name__)


def embedded_cover_bytes(file_path: str) -> tuple[bytes, str] | None:
    """Read embedded artwork from an audio file → (bytes, mime), or None.

    Soft-fail: any mutagen parse error, OS error, or missing/oddly-tagged file
    returns None instead of raising — this is the de-500 fix. Supports ID3
    (MP3/AIFF), MP4/M4A, and FLAC picture blocks.
    """
    try:
        import mutagen

        audio = mutagen.File(file_path)
        if audio is None:
            return None

        # ID3 (MP3, AIFF/WAV)
        tags = getattr(audio, "tags", None)
        if tags:
            for key in tags:
                if key.startswith("APIC"):
                    apic = tags[key]
                    return apic.data, (apic.mime or "image/jpeg")
            # MP4 / M4A
            if "covr" in tags and tags["covr"]:
                return bytes(tags["covr"][0]), "image/jpeg"

        # FLAC
        pics = getattr(audio, "pictures", None)
        if pics:
            return pics[0].data, (pics[0].mime or "image/jpeg")
    except Exception:  # noqa: BLE001 — artwork must never raise to the client
        logger.warning("Embedded artwork read failed for %s", file_path, exc_info=True)
        return None
    return None


def _album_cover_track(session: Session, album_names: list[str]) -> Track | None:
    """The album's representative track: lowest (disc, track, file_path)."""
    return (
        session.query(Track)
        .filter(Track.album.in_(album_names))
        .order_by(
            Track.disc_number.is_(None),
            Track.disc_number.asc(),
            Track.track_number.is_(None),
            Track.track_number.asc(),
            Track.file_path.asc(),
        )
        .first()
    )


def resolve_album_cover(
    session: Session,
    album_key: str,
    *,
    transport: httpx.BaseTransport | None = None,
) -> tuple["object", str] | None:
    """Resolve an album's cover, caching the winner. Returns (path, source) or None.

    `transport` is injected in tests so the network sources stay offline; in
    production it's None and the real endpoints are used.
    """
    resolved = find_album_by_key(session, album_key)
    if not resolved:
        return None
    album_names, artist, _is_comp = resolved
    md = session.get(AlbumMetadata, album_key)

    # 1. Disk cache hit — serve whatever source previously won.
    cached = cached_cover_path(album_key)
    if cached:
        return cached, (md.cover_source if md and md.cover_source else "cache")

    # Respect a fresh "no cover" sentinel (TTL'd) to keep request volume near zero.
    if is_cover_known_missing(album_key):
        return None

    album_name = album_names[0]

    # 2. Embedded artwork of the album's cover track (soft-fail).
    cover_track = _album_cover_track(session, album_names)
    if cover_track and cover_track.file_path:
        from kiku.db.paths import normalize_path

        emb = embedded_cover_bytes(normalize_path(cover_track.file_path))
        if emb:
            content, ct = emb
            path = store_cover(album_key, content, ct)
            if path:
                _record_source(session, md, album_key, album_name, artist, "embedded")
                return path, "embedded"

    # 3. Cover Art Archive — only when we already know the MB release (no new lookup).
    if md and md.mb_release_id:
        path = fetch_front_cover(md.mb_release_id, album_key, transport=transport)
        if path:
            _record_source(session, md, album_key, album_name, artist, "caa")
            return path, "caa"

    # 4 & 5. External cover sources, in order.
    from kiku.artwork.deezer import DeezerClient
    from kiku.artwork.itunes import ItunesClient

    for source_name, client in (
        ("itunes", ItunesClient(transport=transport)),
        ("deezer", DeezerClient(transport=transport)),
    ):
        result = client.search_cover(artist, album_name)
        if result:
            content, ct = result
            path = store_cover(album_key, content, ct)
            if path:
                _record_source(session, md, album_key, album_name, artist, source_name)
                return path, source_name

    # 6. Nothing found — stamp the sentinel so repeat views don't re-hit the network.
    mark_cover_missing(album_key)
    return None


def _record_source(
    session: Session,
    md: AlbumMetadata | None,
    album_key: str,
    album: str,
    artist: str,
    source: str,
) -> None:
    if md is None:
        md = AlbumMetadata(album_key=album_key, album=album, album_artist=artist)
        session.add(md)
    md.cover_source = source
    md.cover_fetched_at = datetime.utcnow()
    try:
        session.commit()
    except Exception:  # noqa: BLE001 — provenance write must not break image serving
        logger.warning("Failed to record cover_source for %s", album_key, exc_info=True)
        session.rollback()
