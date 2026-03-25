"""Shared export utilities -- path aliasing and validation."""

from __future__ import annotations

import re
from pathlib import Path

# Path aliases: (macOS prefix, Linux prefix).
# Reverse of sync.py's _PATH_ALIASES — export converts Linux back to macOS.
_PATH_ALIASES: list[tuple[str, str]] = [
    ("/Volumes/", "/run/media/mantis/"),
]


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
