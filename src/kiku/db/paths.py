"""Cross-platform path normalization for track matching.

Rekordbox stores macOS paths (/Volumes/SSD/...); on Linux the same drives
mount under /run/media/<user>/SSD/...  This module provides a single
canonical form so that scan and sync can both match tracks regardless of
which OS originally imported them.
"""

from __future__ import annotations

# Known mount-point mappings between macOS and Linux.
_PATH_ALIASES: list[tuple[str, str]] = [
    ("/Volumes/", "/run/media/mantis/"),
]


def normalize_path(path: str) -> str:
    """Return a canonical form of *path* for cross-platform matching.

    Replaces known macOS mount prefixes with their Linux equivalents so that
    a track stored under ``/Volumes/SSD/...`` matches ``/run/media/mantis/SSD/...``.
    """
    for mac_prefix, linux_prefix in _PATH_ALIASES:
        if path.startswith(mac_prefix):
            return linux_prefix + path[len(mac_prefix):]
        if path.startswith(linux_prefix):
            return linux_prefix + path[len(linux_prefix):]
    return path
