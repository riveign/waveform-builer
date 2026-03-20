"""Shared regex patterns for tracklist extraction."""

from __future__ import annotations

import re

# Timestamp patterns: "01:23:45", "1:23:45", "23:45", "1:23"
TIMESTAMP_RE = re.compile(
    r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})"
)

# "Artist - Title" or "Artist — Title" (em-dash)
ARTIST_TITLE_RE = re.compile(
    r"^(.+?)\s*[-–—]\s*(.+)$"
)

# Remix/edit detection: "Title (Artist Remix)" or "Title [Artist Edit]"
REMIX_RE = re.compile(
    r"^(.*?)\s*[\(\[](.*?(?:remix|edit|bootleg|rework|dub|mix|version|vip))[\)\]](.*)$",
    re.IGNORECASE,
)

# Numbered tracklist: "1. Artist - Title" or "01) Artist - Title"
NUMBERED_LINE_RE = re.compile(
    r"^\s*(\d{1,3})\s*[.\)]\s*(.+)$"
)

# Timestamp + track line: "01:23:45 Artist - Title" or "[01:23] Artist - Title"
TIMESTAMPED_LINE_RE = re.compile(
    r"^\s*\[?" + TIMESTAMP_RE.pattern + r"\]?\s+(.+)$"
)

# YouTube "Music in this video" section markers
YT_MUSIC_SECTION_RE = re.compile(
    r"(?:music|tracks?\s+(?:in|used)|tracklist|setlist)\s*(?:in this video)?",
    re.IGNORECASE,
)


def parse_timestamp(text: str) -> float | None:
    """Parse a timestamp string to seconds. Returns None if not a timestamp."""
    m = TIMESTAMP_RE.search(text)
    if not m:
        return None
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2))
    seconds = int(m.group(3))
    return hours * 3600 + minutes * 60 + seconds


def parse_artist_title(text: str) -> tuple[str, str] | None:
    """Extract (artist, title) from 'Artist - Title' format. Returns None if no separator."""
    text = text.strip()
    m = ARTIST_TITLE_RE.match(text)
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()


def parse_remix(title: str) -> tuple[str, str | None]:
    """Extract remix info from title. Returns (clean_title, remix_info).
    If no remix detected, remix_info is None.
    """
    m = REMIX_RE.match(title)
    if not m:
        return title.strip(), None
    clean = (m.group(1) + m.group(3)).strip()
    remix = m.group(2).strip()
    return clean, remix


def normalize_name(name: str) -> str:
    """Normalize artist/title for matching: lowercase, strip feat/ft, trim whitespace."""
    name = name.lower().strip()
    # Remove featuring credits
    name = re.sub(r"\s*(feat\.?|ft\.?|featuring)\s+.*$", "", name, flags=re.IGNORECASE)
    # Remove extra whitespace
    name = re.sub(r"\s+", " ", name)
    return name
