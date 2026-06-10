"""MusicBrainz source — wraps the existing throttled MB client."""

from __future__ import annotations

import logging

from kiku.metadata.models import RecordingCandidate, ReleaseCandidate
from kiku.metadata.sources.base import LookupUnsupported

logger = logging.getLogger(__name__)


class MusicBrainzSource:
    name = "musicbrainz"

    def __init__(self, client=None) -> None:
        if client is None:
            from kiku.musicbrainz.client import MusicBrainzClient

            client = MusicBrainzClient()
        self._client = client

    def available(self) -> bool:
        return True

    def search(self, album: str, artist: str, *, limit: int = 3) -> list[ReleaseCandidate]:
        raw = self._client.search_releases(album, artist, limit=limit)
        candidates: list[ReleaseCandidate] = []
        for cand in raw:
            mb_id = cand.get("id")
            if not mb_id:
                continue
            try:
                full = self._client.get_release(mb_id)
            except Exception:  # noqa: BLE001
                logger.warning("MB detail fetch failed for %s", mb_id)
                continue
            candidates.append(self._to_candidate(full, mb_id))
        return candidates

    def fetch_url(self, url: str) -> ReleaseCandidate | None:
        raise LookupUnsupported("MusicBrainz is searched by album+artist, not by URL")

    def _to_candidate(self, full: dict, mb_id: str) -> ReleaseCandidate:
        recordings: list[RecordingCandidate] = []
        for medium in full.get("media", []) or []:
            disc_no = int(medium.get("position", 1) or 1)
            for tr in medium.get("tracks", []) or []:
                pos = tr.get("position")
                title = (tr.get("title") or "").strip()
                if not (pos and title):
                    continue
                length = tr.get("length")
                recordings.append(RecordingCandidate(
                    title=title,
                    position=int(pos),
                    disc=disc_no,
                    length_ms=int(length) if length else None,
                ))

        label_info = full.get("label-info") or []
        label = None
        if label_info and label_info[0].get("label"):
            label = label_info[0]["label"].get("name")

        return ReleaseCandidate(
            source=self.name,
            source_id=mb_id,
            url=f"https://musicbrainz.org/release/{mb_id}",
            album=full.get("title"),
            artist=_format_artist(full.get("artist-credit")),
            label=label,
            year=_year_from_date(full.get("date")),
            recordings=recordings,
        )


def _format_artist(artist_credit) -> str | None:
    if not artist_credit:
        return None
    parts: list[str] = []
    for ac in artist_credit:
        if isinstance(ac, str):
            parts.append(ac)
        elif isinstance(ac, dict):
            parts.append(ac.get("name") or (ac.get("artist") or {}).get("name", ""))
    return "".join(parts).strip() or None


def _year_from_date(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        return int(date_str[:4])
    except (ValueError, TypeError):
        return None
