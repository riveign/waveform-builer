"""Parse Rekordbox M3U8 playlist exports.

Handles UTF-8 BOM, NFC/NFD Unicode normalization, Windows backslashes,
and the #PLAYLIST tag for set name override.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from kiku.db.paths import normalize_path


@dataclass
class M3U8Track:
    path: str  # Raw path from M3U8
    normalized_path: str  # After normalize_path() + NFC
    title: str | None  # From #EXTINF display title
    duration_sec: int  # From #EXTINF duration (-1 if unknown)
    line_number: int  # Source line for error reporting


@dataclass
class M3U8ParseResult:
    tracks: list[M3U8Track] = field(default_factory=list)
    playlist_name: str = ""  # From #PLAYLIST tag or filename
    source_path: str = ""  # Original file path
    warnings: list[str] = field(default_factory=list)


def _normalize_m3u8_path(raw_path: str) -> str:
    """NFC-normalize + backslash convert + normalize_path()."""
    p = raw_path.strip()
    p = p.replace("\\", "/")
    p = unicodedata.normalize("NFC", p)
    return normalize_path(p)


def parse_m3u8(content: str, *, source_path: str = "") -> M3U8ParseResult:
    """Parse M3U8 content string into tracks.

    Parameters
    ----------
    content : str
        Raw M3U8 file content (BOM should already be stripped by caller
        using utf-8-sig encoding).
    source_path : str
        Original file path for error reporting and default set name.
    """
    result = M3U8ParseResult(source_path=source_path)

    # Default name from filename (without extension)
    if source_path:
        result.playlist_name = Path(source_path).stem

    # Strip BOM if present in content itself
    if content.startswith("\ufeff"):
        content = content[1:]

    lines = content.splitlines()

    # Check for #EXTM3U header
    has_header = bool(lines) and lines[0].strip().startswith("#EXTM3U")

    if not has_header:
        result.warnings.append("Missing #EXTM3U header — parsing anyway")

    pending_extinf: tuple[int, str | None] | None = None  # (duration, title)
    pending_line: int = 0

    for line_num, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        # Skip empty lines
        if not line:
            continue

        # #PLAYLIST tag — set name override
        if line.startswith("#PLAYLIST:"):
            result.playlist_name = line[len("#PLAYLIST:"):].strip()
            continue

        # #EXTINF — parse duration and display title
        if line.startswith("#EXTINF:"):
            info = line[len("#EXTINF:"):]
            comma_idx = info.find(",")
            if comma_idx >= 0:
                try:
                    duration = int(info[:comma_idx].strip())
                except ValueError:
                    duration = -1
                title = info[comma_idx + 1:].strip() or None
            else:
                # Malformed — try to parse just the number
                try:
                    duration = int(info.strip())
                except ValueError:
                    duration = -1
                title = None
                result.warnings.append(f"Line {line_num}: malformed #EXTINF (no comma)")
            pending_extinf = (duration, title)
            pending_line = line_num
            continue

        # Skip other comment/directive lines
        if line.startswith("#"):
            continue

        # This is a file path line
        raw_path = line
        norm_path = _normalize_m3u8_path(raw_path)

        duration = -1
        title = None
        ref_line = line_num

        if pending_extinf is not None:
            duration, title = pending_extinf
            ref_line = pending_line
            pending_extinf = None

        result.tracks.append(M3U8Track(
            path=raw_path,
            normalized_path=norm_path,
            title=title,
            duration_sec=duration,
            line_number=ref_line,
        ))

    return result


def parse_m3u8_file(file_path: str) -> M3U8ParseResult:
    """Read and parse an M3U8 file from disk."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    # utf-8-sig strips BOM automatically
    content = path.read_text(encoding="utf-8-sig")
    return parse_m3u8(content, source_path=str(path))
