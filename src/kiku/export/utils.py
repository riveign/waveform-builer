"""Shared export utilities -- path aliasing and validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Path aliases: (macOS prefix, Linux prefix).
# Reverse of sync.py's _PATH_ALIASES — export converts Linux back to macOS.
_PATH_ALIASES: list[tuple[str, str]] = [
    ("/Volumes/", "/run/media/mantis/"),
]


@dataclass
class SkippedTrack:
    """A track that couldn't go in the playlist, and why."""

    track_id: int
    title: str
    artist: str | None
    reason: str  # human-readable: "on vinyl — side B2"


@dataclass
class ExportResult:
    """Where the file went, and what didn't make it in.

    Rekordbox reads a missing Location as a corrupt entry, not a placeholder, so
    a fileless track is left out of the playlist and reported here instead —
    the DJ finds out at export time rather than on the booth screen.
    """

    path: str
    skipped: list[SkippedTrack] = field(default_factory=list)


def skip_reason(track) -> str | None:
    """Why this track can't be exported to a file-based playlist, or None."""
    if track.file_path:
        return None
    if track.medium == "vinyl":
        side = f" — side {track.vinyl_position}" if track.vinyl_position else ""
        return f"on vinyl{side}"
    return "no file on disk"


def export_path(file_path: str, target_platform: str = "macos") -> str:
    """Convert Kiku's stored path to the target platform format.

    The database stores Linux-normalised paths (``/run/media/mantis/…``).
    For Rekordbox on macOS these must be reversed to ``/Volumes/…``.
    """
    if target_platform == "macos":
        for mac_prefix, linux_prefix in _PATH_ALIASES:
            if file_path.startswith(linux_prefix):
                return mac_prefix + file_path[len(linux_prefix) :]
    return file_path


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    return re.sub(r'[/\\:*?"<>|]', "_", name)


def validate_track_paths(
    file_paths: list[str],
) -> tuple[list[str], list[str]]:
    """Check which track file paths exist on disk.

    Returns (found, missing) tuple of path lists.
    """
    found: list[str] = []
    missing: list[str] = []
    for fp in file_paths:
        if Path(fp).exists():
            found.append(fp)
        else:
            missing.append(fp)
    return found, missing
