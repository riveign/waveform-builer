"""MusicBrainz HTTP client with 1 req/s throttling and required User-Agent."""

from __future__ import annotations

import logging
import threading
import time

import httpx

logger = logging.getLogger(__name__)

MB_BASE_URL = "https://musicbrainz.org/ws/2"
DEFAULT_USER_AGENT = "Kiku/0.1 ( riveign@gmail.com )"
MIN_REQUEST_INTERVAL_S = 1.0
DEFAULT_TIMEOUT_S = 15.0


class MusicBrainzClient:
    """Thin sync wrapper over httpx with a process-wide 1 req/s gate."""

    _last_request_at: float = 0.0
    _lock = threading.Lock()

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        transport: httpx.BaseTransport | None = None,
        timeout: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self._user_agent = user_agent
        self._client = httpx.Client(
            base_url=MB_BASE_URL,
            timeout=timeout,
            transport=transport,
            headers={"User-Agent": user_agent, "Accept": "application/json"},
        )

    def __enter__(self) -> "MusicBrainzClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _throttle(self) -> None:
        with MusicBrainzClient._lock:
            now = time.monotonic()
            wait = MIN_REQUEST_INTERVAL_S - (now - MusicBrainzClient._last_request_at)
            if wait > 0:
                time.sleep(wait)
            MusicBrainzClient._last_request_at = time.monotonic()

    def _get(self, path: str, params: dict | None = None) -> dict:
        self._throttle()
        resp = self._client.get(path, params=params or {})
        resp.raise_for_status()
        return resp.json()

    def search_releases(self, album: str, artist: str, limit: int = 3) -> list[dict]:
        """Search releases by album + artist. Returns the `releases` list from MB JSON."""
        query = f'release:"{_escape(album)}" AND artist:"{_escape(artist)}"'
        data = self._get(
            "/release/",
            params={"query": query, "fmt": "json", "limit": limit},
        )
        return data.get("releases", []) or []

    def get_release(self, mb_release_id: str) -> dict:
        """Fetch a release with recordings (tracklist) inline."""
        return self._get(
            f"/release/{mb_release_id}",
            params={"inc": "recordings+artist-credits+labels", "fmt": "json"},
        )


def _escape(s: str) -> str:
    # Strip MB-reserved chars that break the Lucene query parser
    return (
        s.replace("\\", " ")
        .replace('"', " ")
        .replace(":", " ")
        .replace("(", " ")
        .replace(")", " ")
        .strip()
    )
