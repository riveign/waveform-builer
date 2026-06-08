"""iTunes Search API cover source (no auth).

GET https://itunes.apple.com/search?term=<artist album>&entity=album&limit=5
Keep results with collectionType == "Album", pick the best by fuzzy match, and
upscale the 100px thumbnail to 600px (verified 200 image/jpeg).
"""

from __future__ import annotations

import logging
import threading
import time

import httpx

from kiku.artwork.match import accept, score_candidate
from kiku.artwork.util import USER_AGENT, download_image

logger = logging.getLogger(__name__)

ITUNES_BASE_URL = "https://itunes.apple.com"
MIN_REQUEST_INTERVAL_S = 0.34  # ~3 req/s; public no-auth endpoint
DEFAULT_TIMEOUT_S = 15.0


class ItunesClient:
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
        with ItunesClient._lock:
            wait = MIN_REQUEST_INTERVAL_S - (time.monotonic() - ItunesClient._last_request_at)
            if wait > 0:
                time.sleep(wait)
            ItunesClient._last_request_at = time.monotonic()

    def search_cover(self, artist: str | None, album: str | None) -> tuple[bytes, str] | None:
        """Return (image_bytes, content_type) for the best album match, or None."""
        if not album:
            return None
        term = " ".join(p for p in [artist or "", album] if p).strip()
        self._throttle()
        try:
            with httpx.Client(
                base_url=ITUNES_BASE_URL,
                timeout=self._timeout,
                transport=self._transport,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            ) as client:
                resp = client.get(
                    "/search",
                    params={"term": term, "entity": "album", "limit": 5},
                )
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError):
            logger.warning("iTunes search failed for %r", term, exc_info=True)
            return None

        best_url: str | None = None
        best_score = 0.0
        for r in data.get("results", []) or []:
            if r.get("collectionType") not in (None, "Album"):
                continue
            score = score_candidate(
                artist, album, r.get("artistName"), r.get("collectionName")
            )
            if accept(score) and score > best_score and r.get("artworkUrl100"):
                best_score = score
                best_url = _upscale(r["artworkUrl100"])

        if not best_url:
            return None
        return download_image(best_url, transport=self._transport)


def _upscale(artwork_url_100: str) -> str:
    """Replace the 100x100 thumbnail segment with 600x600 for a larger image."""
    return artwork_url_100.replace("100x100bb.jpg", "600x600bb.jpg")
