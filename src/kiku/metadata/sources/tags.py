"""Embedded-tags source — read the album's own files as the source of truth.

Independent of Rekordbox sync: whatever the WAV/AIFF/MP3 files actually carry
in their metadata. Useful when the on-disk tags are right but the synced DB
row drifted. Unlike the network sources, this one is fed file paths directly
rather than searched.
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

from kiku.metadata.models import RecordingCandidate, ReleaseCandidate
from kiku.metadata.sources.base import LookupUnsupported

logger = logging.getLogger(__name__)


class TagsSource:
    name = "tags"

    def available(self) -> bool:
        return True

    def search(self, album: str, artist: str, *, limit: int = 3) -> list[ReleaseCandidate]:
        raise LookupUnsupported("Embedded tags are read from the album's files, not searched")

    def fetch_url(self, url: str) -> ReleaseCandidate | None:
        raise LookupUnsupported("Embedded tags are read from the album's files, not a URL")

    def from_paths(self, paths: list[str]) -> ReleaseCandidate | None:
        """Build one release candidate from a set of audio file paths."""
        recordings: list[RecordingCandidate] = []
        albums: Counter[str] = Counter()
        artists: Counter[str] = Counter()
        labels: Counter[str] = Counter()
        years: Counter[int] = Counter()

        for p in paths:
            tags = _read_tags(p)
            if tags is None:
                continue
            title = tags.get("title") or Path(p).stem
            recordings.append(RecordingCandidate(
                title=title.strip(),
                position=tags.get("track_number"),
                disc=tags.get("disc_number") or 1,
                artist=tags.get("artist"),
                length_ms=tags.get("length_ms"),
            ))
            if tags.get("album"):
                albums[tags["album"]] += 1
            if tags.get("artist"):
                artists[tags["artist"]] += 1
            if tags.get("label"):
                labels[tags["label"]] += 1
            if tags.get("year"):
                years[tags["year"]] += 1

        if not recordings:
            return None

        # Order by track number when present, else keep file order.
        recordings.sort(key=lambda r: (r.position is None, r.position or 0))

        return ReleaseCandidate(
            source=self.name,
            source_id="embedded",
            album=_most_common(albums),
            artist=_most_common(artists),
            label=_most_common(labels),
            year=_most_common(years),
            recordings=recordings,
        )


def _most_common(counter: Counter):
    return counter.most_common(1)[0][0] if counter else None


def _read_tags(path: str) -> dict | None:
    try:
        from mutagen import File as MutagenFile
    except ImportError:  # pragma: no cover
        logger.warning("mutagen not installed; tags source unavailable")
        return None

    try:
        audio = MutagenFile(path, easy=True)
    except Exception:  # noqa: BLE001
        audio = None
    if audio is None:
        # Retry without easy mode (e.g. WAV with raw ID3 / INFO chunks).
        try:
            audio = MutagenFile(path)
        except Exception:  # noqa: BLE001
            return None
    if audio is None:
        return None

    def first(*keys: str) -> str | None:
        for k in keys:
            val = audio.get(k)
            if val:
                v = val[0] if isinstance(val, list) else val
                s = str(v).strip()
                if s:
                    return s
        return None

    out: dict = {
        "title": first("title", "TIT2"),
        "artist": first("artist", "TPE1"),
        "album": first("album", "TALB"),
        "label": first("label", "organization", "TPUB"),
    }
    out["track_number"] = _parse_int(first("tracknumber", "TRCK"))
    out["disc_number"] = _parse_int(first("discnumber", "TPOS"))
    out["year"] = _parse_year(first("date", "originaldate", "year", "TDRC"))
    info = getattr(audio, "info", None)
    if info is not None and getattr(info, "length", None):
        out["length_ms"] = int(info.length * 1000)
    return out


def _parse_int(text: str | None) -> int | None:
    if not text:
        return None
    # tracknumber is often "3/8" or "A1"; take the leading integer.
    digits = ""
    for ch in text:
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    return int(digits) if digits else None


def _parse_year(text: str | None) -> int | None:
    if not text:
        return None
    for i in range(len(text) - 3):
        chunk = text[i:i + 4]
        if chunk.isdigit():
            return int(chunk)
    return None
