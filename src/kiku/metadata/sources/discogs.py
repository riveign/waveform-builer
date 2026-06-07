"""Discogs source — release lookup via the Discogs API.

Discogs is the strongest source for vinyl/electronic catalog data (side
positions like A1/B2). It needs a free personal token, read from
`[discogs] token` in ~/.kiku/config.toml or the KIKU_DISCOGS_TOKEN env var;
without one the source reports itself unavailable.
"""

from __future__ import annotations

import logging
import os
import re

import httpx

from kiku.metadata.models import RecordingCandidate, ReleaseCandidate
from kiku.metadata.sources.base import LookupUnsupported, SourceUnavailable

logger = logging.getLogger(__name__)

API_BASE = "https://api.discogs.com"
USER_AGENT = "Kiku/0.1 ( riveign@gmail.com )"
TIMEOUT_S = 15.0
_RELEASE_URL_RE = re.compile(r"/release[s]?/(\d+)")
_DURATION_RE = re.compile(r"^(\d+):(\d{1,2})$")


def get_discogs_token() -> str | None:
    env = os.environ.get("KIKU_DISCOGS_TOKEN")
    if env:
        return env
    from kiku.config import _get

    token = _get("discogs", "token", None)
    return token or None


class DiscogsSource:
    name = "discogs"

    def __init__(self, token: str | None = None, transport: httpx.BaseTransport | None = None) -> None:
        self._token = token if token is not None else get_discogs_token()
        self._transport = transport

    def available(self) -> bool:
        return bool(self._token)

    def search(self, album: str, artist: str, *, limit: int = 3) -> list[ReleaseCandidate]:
        self._require_token()
        data = self._get(
            "/database/search",
            params={
                "release_title": album,
                "artist": artist,
                "type": "release",
                "per_page": limit,
            },
        )
        results = (data or {}).get("results", []) or []
        candidates: list[ReleaseCandidate] = []
        for r in results[:limit]:
            rid = r.get("id")
            if not rid:
                continue
            cand = self._fetch_release(int(rid))
            if cand:
                candidates.append(cand)
        return candidates

    def fetch_url(self, url: str) -> ReleaseCandidate | None:
        self._require_token()
        m = _RELEASE_URL_RE.search(url)
        if not m:
            raise LookupUnsupported("Not a Discogs release URL (expected /release/<id>)")
        return self._fetch_release(int(m.group(1)))

    def _require_token(self) -> None:
        if not self._token:
            raise SourceUnavailable(
                "Discogs needs a token — set it with `kiku config set discogs.token <TOKEN>`"
            )

    def _fetch_release(self, release_id: int) -> ReleaseCandidate | None:
        full = self._get(f"/releases/{release_id}")
        if not full:
            return None
        return self._to_candidate(full, release_id)

    def _to_candidate(self, full: dict, release_id: int) -> ReleaseCandidate:
        recordings: list[RecordingCandidate] = []
        pos = 0
        for tr in full.get("tracklist", []) or []:
            if (tr.get("type_") or "track") != "track":
                continue  # skip headings / index tracks
            title = (tr.get("title") or "").strip()
            if not title:
                continue
            pos += 1
            recordings.append(RecordingCandidate(
                title=title,
                position=pos,
                disc=1,
                length_ms=_duration_to_ms(tr.get("duration")),
            ))

        labels = full.get("labels") or []
        label = labels[0].get("name") if labels and labels[0].get("name") else None
        artists = full.get("artists") or []
        artist = _join_artists(artists)

        return ReleaseCandidate(
            source=self.name,
            source_id=str(release_id),
            url=full.get("uri") or f"https://www.discogs.com/release/{release_id}",
            album=(full.get("title") or "").strip() or None,
            artist=artist,
            label=label,
            year=full.get("year") or None,
            recordings=recordings,
        )

    def _get(self, path: str, params: dict | None = None) -> dict | None:
        headers = {"User-Agent": USER_AGENT}
        if self._token:
            headers["Authorization"] = f"Discogs token={self._token}"
        try:
            with httpx.Client(
                base_url=API_BASE,
                timeout=TIMEOUT_S,
                transport=self._transport,
                headers=headers,
            ) as client:
                resp = client.get(path, params=params or {})
                resp.raise_for_status()
                return resp.json()
        except Exception:  # noqa: BLE001
            logger.exception("Discogs request failed: %s", path)
            return None


def _join_artists(artists: list[dict]) -> str | None:
    parts: list[str] = []
    for a in artists:
        name = (a.get("name") or "").strip()
        if not name:
            continue
        # Discogs disambiguates duplicate names with a trailing "(n)".
        name = re.sub(r"\s*\(\d+\)$", "", name)
        parts.append(name)
        join = (a.get("join") or "").strip()
        if join and join != ",":
            parts.append(join)
        elif join == ",":
            parts.append(",")
    out = " ".join(parts).replace(" ,", ",").strip()
    return out or None


def _duration_to_ms(text: str | None) -> int | None:
    if not text:
        return None
    m = _DURATION_RE.match(text.strip())
    if not m:
        return None
    return (int(m.group(1)) * 60 + int(m.group(2))) * 1000
