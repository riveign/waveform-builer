"""Turn a pressing's side string into something you can sort by.

`vinyl_position` keeps the raw Discogs string because that is what is printed
on the label and what the DJ reads when pulling the record. Ordering comes from
parsing it into the two columns Kiku already sorts albums by:

    disc_number  = side ordinal   (A=1, B=2, C=3, D=4 …)
    track_number = index within that side

For a 2×LP this makes `disc_number` mean *side*, not *disc*. That is deliberate:
the side is the unit of DJ action — you flip a side, you never flip a disc.
"""

from __future__ import annotations

import re

# "A1", "B2", "AA1", "C", "A-1"
_SIDE_RE = re.compile(r"^\s*([A-Za-z]{1,2})\s*[-.]?\s*(\d+)?\s*$")
_TRAILING_NUM_RE = re.compile(r"(\d+)\s*$")


def parse_position(raw: str | None) -> tuple[int | None, int | None]:
    """Return (side_ordinal, index_within_side) for a raw position string.

    >>> parse_position("A1")
    (1, 1)
    >>> parse_position("B2")
    (2, 2)
    >>> parse_position("C")
    (3, None)
    >>> parse_position("AA3")
    (27, 3)
    >>> parse_position("Digi 1")
    (None, 1)
    >>> parse_position("4")
    (None, 4)
    >>> parse_position(None)
    (None, None)
    """
    if not raw or not raw.strip():
        return (None, None)

    text = raw.strip()
    m = _SIDE_RE.match(text)
    if m:
        side = _side_ordinal(m.group(1))
        idx = int(m.group(2)) if m.group(2) else None
        return (side, idx)

    # Anything else ("Digi 1", "CD1-3", "Bonus 2") has no pressing side. Keep the
    # trailing number so the track still orders sensibly after the sides.
    tail = _TRAILING_NUM_RE.search(text)
    return (None, int(tail.group(1)) if tail else None)


def _side_ordinal(letters: str) -> int:
    """A=1 … Z=26, AA=27 … — base-26 so a 3xLP's sides stay in order."""
    value = 0
    for ch in letters.upper():
        value = value * 26 + (ord(ch) - ord("A") + 1)
    return value


def side_letter(ordinal: int | None) -> str | None:
    """Inverse of `_side_ordinal`, for display: 1 -> 'A', 27 -> 'AA'."""
    if not ordinal or ordinal < 1:
        return None
    out = ""
    n = ordinal
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(ord("A") + rem) + out
    return out
