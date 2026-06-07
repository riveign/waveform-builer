"""Stable album identity — shared by the albums API and the fix-album CLI.

An album_key is a hash of (normalized album, normalized album-artist). It groups
casing/whitespace variants and survives across sessions, so a correction made in
the CLI and one made in the browser address the same album.
"""

from __future__ import annotations

import hashlib
import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from kiku.db.models import Track

_WS_RE = re.compile(r"\s+")


def normalize(s: str | None) -> str:
    if not s:
        return ""
    return _WS_RE.sub(" ", s.strip().lower())


def album_key(album: str, artist: str) -> str:
    raw = f"{normalize(album)}|{normalize(artist)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def classify_artist(artist_count: int, any_artist: str | None) -> tuple[str, bool]:
    """Resolve album_artist + is_compilation from aggregate counts.

    COUNT(DISTINCT) and MIN() both ignore NULLs in SQL, so:
      0 → all NULL → "Unknown Artist"
      1 → single artist → use it
      >1 → "Various Artists" + compilation
    """
    if artist_count > 1:
        return "Various Artists", True
    if artist_count == 1 and any_artist:
        return any_artist, False
    return "Unknown Artist", False


def resolve_album_artist(session: Session, album: str) -> tuple[str, bool]:
    """Single-album lookup used by detail endpoints (tracks / cover / fix)."""
    row = (
        session.query(
            func.count(func.distinct(Track.artist)).label("artist_count"),
            func.min(Track.artist).label("any_artist"),
        )
        .filter(Track.album == album)
        .one()
    )
    return classify_artist(row.artist_count or 0, row.any_artist)


def find_album_by_key(session: Session, key: str) -> tuple[list[str], str, bool] | None:
    """Find (album_names, album_artist, is_compilation) matching an album_key.

    Multiple raw album names can normalize to the same key (casing variants like
    "Hard Work" / "Hard work"); all variants are returned so downstream queries
    can span them via `Track.album.in_(names)`.
    """
    rows = (
        session.query(
            Track.album.label("album"),
            func.count(func.distinct(Track.artist)).label("artist_count"),
            func.min(Track.artist).label("any_artist"),
        )
        .filter(Track.album.isnot(None), Track.album != "")
        .group_by(Track.album)
        .all()
    )
    matches: list[tuple[str, str, bool]] = []
    for album, artist_count, any_artist in rows:
        if not album:
            continue
        artist, is_comp = classify_artist(artist_count or 0, any_artist)
        if album_key(album, artist) == key:
            matches.append((album, artist, is_comp))
    if not matches:
        return None
    names = [m[0] for m in matches]
    return names, matches[0][1], any(m[2] for m in matches)
