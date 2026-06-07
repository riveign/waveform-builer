"""Cover Art Archive (CAA) fetcher.

CAA is MusicBrainz's image service. A release with cover art has:
    GET https://coverartarchive.org/release/{mb_release_id}/front
returning the front image directly (CDN-redirected). 404 means no cover available.

We cache hits on disk under data/cover_art/{album_key}.jpg and mark 404s with a
sibling sentinel `{album_key}.missing` so we don't re-hit the network indefinitely.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

CAA_BASE_URL = "https://coverartarchive.org"
USER_AGENT = "Kiku/0.1 ( riveign@gmail.com )"
DEFAULT_TIMEOUT_S = 20.0
MAX_BYTES = 8 * 1024 * 1024  # 8 MB sanity cap


def cover_art_dir() -> Path:
    """Return (and create) the on-disk cache directory."""
    base = Path(os.environ.get("KIKU_DATA_DIR", "data")) / "cover_art"
    base.mkdir(parents=True, exist_ok=True)
    return base


def cached_cover_path(album_key: str) -> Path | None:
    """Return the local file for this album if cached, else None.

    Sentinel `.missing` file means CAA already told us there is no cover.
    """
    base = cover_art_dir()
    for ext in ("jpg", "png", "jpeg"):
        p = base / f"{album_key}.{ext}"
        if p.exists():
            return p
    return None


def is_cover_known_missing(album_key: str) -> bool:
    return (cover_art_dir() / f"{album_key}.missing").exists()


def mark_cover_missing(album_key: str) -> None:
    (cover_art_dir() / f"{album_key}.missing").touch()


def fetch_front_cover(
    mb_release_id: str,
    album_key: str,
    *,
    transport: httpx.BaseTransport | None = None,
) -> Path | None:
    """Download the front cover for an MB release; cache and return the path.

    Returns None if CAA has no cover for that release (404) or on any other error.
    Caller is responsible for serving / falling back to track-embedded artwork.
    """
    if not mb_release_id:
        return None

    cached = cached_cover_path(album_key)
    if cached:
        return cached
    if is_cover_known_missing(album_key):
        return None

    url = f"{CAA_BASE_URL}/release/{mb_release_id}/front"
    try:
        with httpx.Client(
            timeout=DEFAULT_TIMEOUT_S,
            transport=transport,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as c:
            resp = c.get(url)
    except httpx.HTTPError:
        logger.exception("CAA fetch raised for release %s", mb_release_id)
        return None

    if resp.status_code == 404:
        mark_cover_missing(album_key)
        return None
    if resp.status_code != 200:
        logger.warning(
            "CAA returned %s for release %s", resp.status_code, mb_release_id
        )
        return None

    content = resp.content
    if not content or len(content) > MAX_BYTES:
        logger.warning("CAA response for %s rejected (size=%d)", mb_release_id, len(content))
        return None

    ext = _ext_for_content_type(resp.headers.get("content-type", ""))
    out = cover_art_dir() / f"{album_key}.{ext}"
    out.write_bytes(content)
    return out


def _ext_for_content_type(ct: str) -> str:
    ct = (ct or "").lower()
    if "png" in ct:
        return "png"
    return "jpg"
