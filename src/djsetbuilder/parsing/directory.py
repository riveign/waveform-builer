"""Parse genre and energy metadata from Rekordbox directory structure.

Expected format: /Volumes/{drive}/Musica/{year}/{month} - {year} - {Genre} [{Energy}]

Examples:
    "09 - 2025 - Rumble Techno Warmup"  -> genre="Rumble Techno", energy="Warmup"
    "06 - 2023 - HardGroove Mid"        -> genre="HardGroove", energy="Mid"
    "03 - 2024 - Techno"                -> genre="Techno", energy=None
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from djsetbuilder.config import ENERGY_TAGS

# Build regex with energy tags as alternation
_ENERGY_PATTERN = "|".join(ENERGY_TAGS)
_DIR_RE = re.compile(
    rf"^(\d{{2}})\s*-\s*(\d{{4}})\s*-\s*(.+?)(?:\s+({_ENERGY_PATTERN}))?$",
    re.IGNORECASE,
)


@dataclass
class DirectoryMeta:
    """Metadata parsed from a music directory name."""

    genre: str | None = None
    energy: str | None = None
    acquired_month: str | None = None  # "YYYY-MM"


def parse_directory_name(name: str) -> DirectoryMeta:
    """Parse a single directory name like '09 - 2025 - Rumble Techno Warmup'."""
    m = _DIR_RE.match(name.strip())
    if not m:
        return DirectoryMeta()

    month, year, genre_raw, energy = m.groups()
    genre = genre_raw.strip()
    # Normalize energy tag to title case
    energy = energy.strip().title() if energy else None
    acquired = f"{year}-{month}"

    return DirectoryMeta(genre=genre, energy=energy, acquired_month=acquired)


def parse_track_path(file_path: str | Path) -> DirectoryMeta:
    """Extract genre/energy metadata from a track's full file path.

    Walks up the path looking for a directory matching the naming pattern.
    """
    path = Path(file_path)
    for parent in path.parents:
        meta = parse_directory_name(parent.name)
        if meta.genre is not None:
            return meta
    return DirectoryMeta()
