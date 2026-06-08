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
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

CAA_BASE_URL = "https://coverartarchive.org"
USER_AGENT = "Kiku/0.1 ( riveign@gmail.com )"
DEFAULT_TIMEOUT_S = 20.0
MAX_BYTES = 8 * 1024 * 1024  # 8 MB sanity cap
# A `.missing` sentinel older than this is treated as stale, so late-added art
# (a release that only got a cover after we first looked) gets re-tried.
COVER_MISSING_TTL_DAYS = 30


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


def is_cover_known_missing(album_key: str, ttl_days: int = COVER_MISSING_TTL_DAYS) -> bool:
    """True if we recently recorded that no cover exists for this album.

    The sentinel expires after `ttl_days`: a stale sentinel is removed and
    reported as not-missing, so a fresh lookup runs (and re-stamps on another
    miss). `ttl_days <= 0` disables expiry (sentinel is permanent).
    """
    sentinel = cover_art_dir() / f"{album_key}.missing"
    if not sentinel.exists():
        return False
    if ttl_days <= 0:
        return True
    try:
        age_s = time.time() - sentinel.stat().st_mtime
    except OSError:
        return True
    if age_s > ttl_days * 86400:
        try:
            sentinel.unlink()
        except OSError:
            pass
        return False
    return True


def mark_cover_missing(album_key: str) -> None:
    sentinel = cover_art_dir() / f"{album_key}.missing"
    # Re-touch to reset the TTL clock even if a stale sentinel lingers.
    sentinel.touch()
    try:
        os.utime(sentinel, None)
    except OSError:
        pass


def store_cover(album_key: str, content: bytes, content_type: str) -> Path | None:
    """Write resolved image bytes to the cache for ANY source; clear any sentinel.

    Returns the cached path, or None if the payload is empty / over the size cap.
    """
    if not content or len(content) > MAX_BYTES:
        logger.warning("Cover for %s rejected (size=%d)", album_key, len(content or b""))
        return None
    ext = _ext_for_content_type(content_type)
    out = cover_art_dir() / f"{album_key}.{ext}"
    out.write_bytes(content)
    sentinel = cover_art_dir() / f"{album_key}.missing"
    if sentinel.exists():
        try:
            sentinel.unlink()
        except OSError:
            pass
    return out


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
