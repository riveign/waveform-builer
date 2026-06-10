"""Deezer Search API cover source (no auth).

GET https://api.deezer.com/search/album?q=<artist album>&limit=5
`cover_xl` (1000px) / `cover_big` (500px) are direct CDN URLs — no upscale needed.
Artist is a nested object → match on `artist.name`.
"""

from __future__ import annotations

import logging
import threading
import time

import httpx

from kiku.artwork.match import accept, score_candidate
from kiku.artwork.util import USER_AGENT, download_image

logger = logging.getLogger(__name__)

DEEZER_BASE_URL = "https://api.deezer.com"
MIN_REQUEST_INTERVAL_S = 0.1  # ~10 req/s; Deezer allows ~50/5s
DEFAULT_TIMEOUT_S = 15.0


class DeezerClient:
    """Mirrors MusicBrainzClient: injectable transport + process-wide throttle."""

    _last_request_at: float = 0.0
    _lock = threading.Lock()

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self._transport = transport
        self._timeout = timeout

    def _throttle(self) -> None:
        with DeezerClient._lock:
            wait = MIN_REQUEST_INTERVAL_S - (time.monotonic() - DeezerClient._last_request_at)
            if wait > 0:
                time.sleep(wait)
            DeezerClient._last_request_at = time.monotonic()

    def search_cover(self, artist: str | None, album: str | None) -> tuple[bytes, str] | None:
        """Return (image_bytes, content_type) for the best album match, or None."""
        if not album:
            return None
        q = " ".join(p for p in [artist or "", album] if p).strip()
        self._throttle()
        try:
            with httpx.Client(
                base_url=DEEZER_BASE_URL,
                timeout=self._timeout,
                transport=self._transport,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            ) as client:
                resp = client.get("/search/album", params={"q": q, "limit": 5})
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError):
            logger.warning("Deezer search failed for %r", q, exc_info=True)
            return None

        best_url: str | None = None
        best_score = 0.0
        for r in data.get("data", []) or []:
            cand_artist = (r.get("artist") or {}).get("name")
            score = score_candidate(artist, album, cand_artist, r.get("title"))
            url = r.get("cover_xl") or r.get("cover_big") or r.get("cover")
            if accept(score) and score > best_score and url:
                best_score = score
                best_url = url

        if not best_url:
            return None
        return download_image(best_url, transport=self._transport)
