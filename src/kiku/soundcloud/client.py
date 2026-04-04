"""SoundCloud API client with auto-refresh on 401."""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

SC_API = "https://api.soundcloud.com"


class SoundCloudClient:
    """Thin wrapper around the SoundCloud API."""

    def __init__(self, access_token: str, refresh_token: str | None = None, on_token_refresh=None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._on_token_refresh = on_token_refresh  # callback(new_access, new_refresh, expires_at)

    def _headers(self) -> dict:
        return {"Authorization": f"OAuth {self.access_token}", "Accept": "application/json"}

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an API request with auto-refresh on 401."""
        url = f"{SC_API}{path}" if path.startswith("/") else path
        resp = httpx.request(method, url, headers=self._headers(), timeout=30, **kwargs)

        if resp.status_code == 401 and self.refresh_token:
            logger.info("SoundCloud token expired, refreshing...")
            self._do_refresh()
            resp = httpx.request(method, url, headers=self._headers(), timeout=30, **kwargs)

        resp.raise_for_status()
        return resp.json()

    def _do_refresh(self):
        """Refresh the access token."""
        from kiku.soundcloud.oauth import refresh_token as do_refresh

        data = do_refresh(self.refresh_token)
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        expires_at = None
        if "expires_in" in data:
            from datetime import timedelta
            expires_at = (datetime.now() + timedelta(seconds=data["expires_in"])).isoformat()

        if self._on_token_refresh:
            self._on_token_refresh(self.access_token, self.refresh_token, expires_at)

    def get_me(self) -> dict:
        """Get current user profile."""
        return self._request("GET", "/me")

    def get_playlists(self) -> list[dict]:
        """Get all playlists for the current user."""
        results = []
        url = "/me/playlists?limit=50"
        while url:
            data = self._request("GET", url)
            items = data.get("collection", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                results.extend(items)
                url = data.get("next_href") if isinstance(data, dict) else None
            else:
                results.extend(items)
                url = data.get("next_href")
        return results

    def get_playlist_tracks(self, playlist_id: int) -> list[dict]:
        """Get tracks in a playlist."""
        data = self._request("GET", f"/playlists/{playlist_id}")
        return data.get("tracks", [])

    def get_likes(self, limit: int = 50, cursor: str | None = None) -> dict:
        """Get liked tracks (paginated).

        Returns dict with 'collection' and 'next_href'.
        """
        params = f"?limit={limit}"
        if cursor:
            params += f"&cursor={cursor}"
        data = self._request("GET", f"/me/likes/tracks{params}")
        return {
            "collection": data.get("collection", []),
            "next_href": data.get("next_href"),
        }
