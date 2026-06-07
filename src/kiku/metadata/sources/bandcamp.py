"""Bandcamp source — scrape a pasted album URL.

Bandcamp embeds the full release as JSON in two places on the album page:
  - a `data-tralbum` attribute (artist + ordered tracklist with durations)
  - an `application/ld+json` block (label, publish date)
We prefer `data-tralbum` for the tracklist and fall back to `ld+json` for the
fields it doesn't carry. No public API or key is involved.
"""

from __future__ import annotations

import json
import logging
import re

import httpx

from kiku.metadata.models import RecordingCandidate, ReleaseCandidate
from kiku.metadata.sources.base import LookupUnsupported

logger = logging.getLogger(__name__)

USER_AGENT = "Kiku/0.1 ( riveign@gmail.com )"
TIMEOUT_S = 15.0
_YEAR_RE = re.compile(r"(\d{4})")


class BandcampSource:
    name = "bandcamp"

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def available(self) -> bool:
        return True

    def search(self, album: str, artist: str, *, limit: int = 3) -> list[ReleaseCandidate]:
        # Bandcamp has no clean release-search API; the DJ pastes the album URL.
        raise LookupUnsupported("Bandcamp is looked up by album URL, not by search")

    def fetch_url(self, url: str) -> ReleaseCandidate | None:
        html = self._get(url)
        if html is None:
            return None
        return parse_bandcamp_html(html, url)

    def _get(self, url: str) -> str | None:
        try:
            with httpx.Client(
                timeout=TIMEOUT_S,
                transport=self._transport,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            ) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.text
        except Exception:  # noqa: BLE001
            logger.exception("Bandcamp fetch failed for %s", url)
            return None


def parse_bandcamp_html(html: str, url: str) -> ReleaseCandidate | None:
    """Extract a ReleaseCandidate from a Bandcamp album page's HTML."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    tralbum = _extract_tralbum(soup)
    ld = _extract_ld_album(soup)

    if not tralbum and not ld:
        return None

    album = None
    artist = None
    recordings: list[RecordingCandidate] = []

    if tralbum:
        current = tralbum.get("current") or {}
        album = (current.get("title") or "").strip() or None
        artist = (tralbum.get("artist") or "").strip() or None
        for i, tr in enumerate(tralbum.get("trackinfo") or [], start=1):
            title = (tr.get("title") or "").strip()
            if not title:
                continue
            dur = tr.get("duration")
            recordings.append(RecordingCandidate(
                title=title,
                position=int(tr.get("track_num") or i),
                disc=1,
                length_ms=int(float(dur) * 1000) if dur else None,
            ))

    # ld+json fills album/artist when tralbum is absent, plus label + year.
    label = None
    year = None
    if ld:
        album = album or (ld.get("name") or "").strip() or None
        by = ld.get("byArtist")
        if not artist and isinstance(by, dict):
            artist = (by.get("name") or "").strip() or None
        label = _ld_label(ld)
        year = _year_from_text(ld.get("datePublished") or ld.get("dateModified"))
        if not recordings:
            recordings = _ld_tracklist(ld)

    if not album and not recordings:
        return None

    return ReleaseCandidate(
        source="bandcamp",
        source_id=url,
        url=url,
        album=album,
        artist=artist,
        label=label,
        year=year,
        recordings=recordings,
    )


def _extract_tralbum(soup) -> dict | None:
    el = soup.find(attrs={"data-tralbum": True})
    if not el:
        return None
    try:
        return json.loads(el["data-tralbum"])
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.warning("Failed to parse data-tralbum JSON")
        return None


def _extract_ld_album(soup) -> dict | None:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for d in candidates:
            if isinstance(d, dict) and d.get("@type") in ("MusicAlbum", "MusicRelease"):
                return d
    return None


def _ld_label(ld: dict) -> str | None:
    for key in ("recordLabel", "publisher"):
        val = ld.get(key)
        if isinstance(val, dict) and val.get("name"):
            return val["name"].strip()
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _ld_tracklist(ld: dict) -> list[RecordingCandidate]:
    track = ld.get("track")
    if not isinstance(track, dict):
        return []
    out: list[RecordingCandidate] = []
    for i, el in enumerate(track.get("itemListElement") or [], start=1):
        item = el.get("item") if isinstance(el, dict) else None
        name = (item or {}).get("name") if isinstance(item, dict) else None
        if not name:
            continue
        pos = el.get("position") if isinstance(el, dict) else None
        out.append(RecordingCandidate(title=name.strip(), position=int(pos or i), disc=1))
    return out


def _year_from_text(text: str | None) -> int | None:
    if not text:
        return None
    m = _YEAR_RE.search(text)
    return int(m.group(1)) if m else None
