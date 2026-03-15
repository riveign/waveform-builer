"""Parse genre and energy metadata from Rekordbox directory structure.

Supported formats:
    Pattern 1 (2023-2025): MM - YYYY - Genre [Energy]
    Pattern 2 (2026+):     YYYY - MM - Genre [Energy]

Examples:
    "09 - 2025 - Rumble Techno Warmup"  -> genre="Rumble Techno", energy="Warmup"
    "06 - 2023 - HardGroove Mid"        -> genre="Hard Groove", energy="Mid"
    "2026 - 01 - Techno Peak"           -> genre="Techno", energy="Peak"
    "04 - 2023 Indie Dance"             -> genre="Indie Dance", energy=None
    "10 - 2023 - Hard Groove - Mid"     -> genre="Hard Groove", energy="Mid"
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from kiku.config import ENERGY_TAGS

# Build regex with energy tags as alternation
_ENERGY_PATTERN = "|".join(ENERGY_TAGS)

# Pattern 1a (2023-2025): MM - YYYY - Genre [Energy] (with second dash)
_DIR_RE_V1 = re.compile(
    rf"^(\d{{2}})\s*-\s*(\d{{4}})\s*-\s*(.+?)(?:\s*-\s*|\s+)({_ENERGY_PATTERN})$",
    re.IGNORECASE,
)
# Pattern 1b: MM - YYYY - Genre (with second dash, no energy)
_DIR_RE_V1_NO_ENERGY = re.compile(
    rf"^(\d{{2}})\s*-\s*(\d{{4}})\s*-\s*(.+)$",
    re.IGNORECASE,
)
# Pattern 1c: MM - YYYY Genre (missing second dash — early 2023 edge case, no energy)
_DIR_RE_V1_NO_DASH = re.compile(
    rf"^(\d{{2}})\s*-\s*(\d{{4}})\s+(.+)$",
    re.IGNORECASE,
)

# Pattern 2 (2026+): YYYY - MM - Genre [Energy]
_DIR_RE_V2 = re.compile(
    rf"^(\d{{4}})\s*-\s*(\d{{2}})\s*-\s*(.+?)(?:\s*-\s*|\s+)({_ENERGY_PATTERN})$",
    re.IGNORECASE,
)
_DIR_RE_V2_NO_ENERGY = re.compile(
    rf"^(\d{{4}})\s*-\s*(\d{{2}})\s*-\s*(.+)$",
    re.IGNORECASE,
)

# Genre normalization map — typos, case variants, compound words, abbreviations
_DEFAULT_GENRE_ALIASES: dict[str, str] = {
    # Typos
    "Acid Techo": "Acid Techno",
    "Hard Stryle Techno": "Hardstyle Techno",
    "Hypno Tehcno": "Hypno Techno",
    "Clasic Techno": "Classic Techno",
    "Techno Groov": "Techno Groove",
    "Rumbel Techno": "Rumble Techno",
    "Ruble Techno": "Rumble Techno",
    "Deep Tehcno": "Deep Techno",
    "Dub Tehcno": "Dub Techno",
    "Tech Hose": "Tech House",
    "Afro Hose": "Afro House",
    "Indei Dance": "Indie Dance",
    "Funkey House": "Funky House",
    # Compound word normalization
    "HardGroove": "Hard Groove",
    "LightGroove": "Light Groove",
    "HardStyle Techno": "Hardstyle Techno",
    "Hard Style Techno": "Hardstyle Techno",
    "HardTechno": "Hard Techno",
    "DeepHouse": "Deep House",
    "TechHouse": "Tech House",
    "AfroHouse": "Afro House",
    "SpeedHouse": "Speed House",
    "HardHouse": "Hard House",
    "FunkyHouse": "Funky House",
    "HardTrance": "Hard Trance",
    "DubTechno": "Dub Techno",
    "AcidTechno": "Acid Techno",
    "IndieDance": "Indie Dance",
    "NuDisco": "Nu Disco",
    "NewWave": "New Wave",
    "PostPunk": "Post Punk",
    "GhettoGroove": "Ghetto Groove",
    # Case normalization
    "deep house": "Deep House",
    "tech house": "Tech House",
    "hard techno": "Hard Techno",
    "acid techno": "Acid Techno",
    "dub techno": "Dub Techno",
    "afro house": "Afro House",
    "nu disco": "Nu Disco",
    "indie dance": "Indie Dance",
    "hard groove": "Hard Groove",
    "light groove": "Light Groove",
    # Abbreviations
    "DnB": "DNB",
    "D&B": "DNB",
    "Drum n Bass": "DNB",
    "Drum & Bass": "DNB",
}

# Single-letter energy abbreviations (from early Trance folders)
ENERGY_ABBREVIATIONS: dict[str, str] = {
    "L": "Low",
    "M": "Mid",
    "U": "Up",
}


def get_genre_aliases() -> dict[str, str]:
    """Return genre aliases merged from defaults + TOML config."""
    from kiku.config import _load_toml

    toml = _load_toml()
    toml_aliases = toml.get("genre_aliases", {})
    return {**_DEFAULT_GENRE_ALIASES, **toml_aliases}


def _normalize_genre(genre: str) -> str:
    """Normalize genre string using alias map and cleanup."""
    genre = genre.strip().rstrip("-").strip()
    aliases = get_genre_aliases()
    return aliases.get(genre, genre)


@dataclass
class DirectoryMeta:
    """Metadata parsed from a music directory name."""

    genre: str | None = None
    energy: str | None = None
    acquired_month: str | None = None  # "YYYY-MM"


def parse_directory_name(name: str) -> DirectoryMeta:
    """Parse a single directory name like '09 - 2025 - Rumble Techno Warmup'.

    Handles both MM-YYYY and YYYY-MM formats, missing dashes,
    and dash-separated energy tags.
    """
    name = name.strip()

    # Try Pattern 2 first (YYYY - MM) — more specific (4-digit year first)
    m = _DIR_RE_V2.match(name)
    if m:
        year, month, genre_raw, energy = m.groups()
        genre = _normalize_genre(genre_raw)
        energy = energy.strip().title() if energy else None
        return DirectoryMeta(
            genre=genre, energy=energy, acquired_month=f"{year}-{month}"
        )

    m = _DIR_RE_V2_NO_ENERGY.match(name)
    if m:
        year, month, genre_raw = m.groups()
        genre = _normalize_genre(genre_raw)
        return DirectoryMeta(
            genre=genre, energy=None, acquired_month=f"{year}-{month}"
        )

    # Try Pattern 1 (MM - YYYY) with energy
    m = _DIR_RE_V1.match(name)
    if m:
        month, year, genre_raw, energy = m.groups()
        genre = _normalize_genre(genre_raw)
        energy = energy.strip().title() if energy else None
        return DirectoryMeta(
            genre=genre, energy=energy, acquired_month=f"{year}-{month}"
        )

    # Try Pattern 1 without energy (with second dash)
    m = _DIR_RE_V1_NO_ENERGY.match(name)
    if m:
        month, year, genre_raw = m.groups()
        genre_raw = genre_raw.strip()

        # Check for single-letter energy abbreviation at end (e.g., "Trance - L")
        energy = None
        abbrev_match = re.match(r"^(.+?)\s*-\s*([A-Z])$", genre_raw)
        if abbrev_match:
            potential_genre, letter = abbrev_match.groups()
            if letter in ENERGY_ABBREVIATIONS:
                genre_raw = potential_genre
                energy = ENERGY_ABBREVIATIONS[letter]

        # Strip trailing numbers that are sequence indicators (e.g., "Deep Techno 01")
        genre_raw = re.sub(r"\s+\d{2,3}$", "", genre_raw)

        genre = _normalize_genre(genre_raw)
        return DirectoryMeta(
            genre=genre, energy=energy, acquired_month=f"{year}-{month}"
        )

    # Try Pattern 1c: missing second dash (e.g., "04 - 2023 Indie Dance")
    m = _DIR_RE_V1_NO_DASH.match(name)
    if m:
        month, year, genre_raw = m.groups()
        genre_raw = genre_raw.strip()
        # Strip trailing sequence numbers
        genre_raw = re.sub(r"\s+\d{2,3}$", "", genre_raw)
        genre = _normalize_genre(genre_raw)
        return DirectoryMeta(
            genre=genre, energy=None, acquired_month=f"{year}-{month}"
        )

    return DirectoryMeta()


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
