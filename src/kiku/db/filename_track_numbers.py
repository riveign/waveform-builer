"""Parse leading disc/track numbers from filenames as a fallback when Rekordbox lacks them."""
from __future__ import annotations

import os
import re


_DISC_TRACK = re.compile(r"^(\d{1,2})[-_](\d{1,2})[\s._-]")
_TRACK_ONLY = re.compile(r"^(\d{1,2})[\s._-]")


def parse_track_position(file_path: str) -> tuple[int | None, int | None]:
    """Return (disc_number, track_number) extracted from filename.

    Disc-track form ``01-18 Title.flac`` -> (1, 18).
    Track-only form ``09 - Title.flac`` -> (None, 9).
    Returns (None, None) if no leading numeric prefix is present.
    Values outside 1..99 are rejected.
    """
    base = os.path.basename(file_path or "")
    m = _DISC_TRACK.match(base)
    if m:
        disc = int(m.group(1))
        track = int(m.group(2))
        if 0 < disc <= 99 and 0 < track <= 99:
            return disc, track
    m = _TRACK_ONLY.match(base)
    if m:
        track = int(m.group(1))
        if 0 < track <= 99:
            return None, track
    return None, None
