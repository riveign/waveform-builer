"""Side strings are display truth; these are the sortable derivation of them."""

from __future__ import annotations

import pytest

from kiku.vinyl.position import parse_position, side_letter


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("A1", (1, 1)),
        ("A2", (1, 2)),
        ("B1", (2, 1)),
        ("D4", (4, 4)),
        ("a1", (1, 1)),
        (" B2 ", (2, 2)),
        ("C", (3, None)),
        ("AA1", (27, 1)),
        ("A-1", (1, 1)),
        ("Digi 1", (None, 1)),
        ("CD1-3", (None, 3)),
        ("4", (None, 4)),
        ("", (None, None)),
        (None, (None, None)),
    ],
)
def test_parse_position(raw, expected):
    assert parse_position(raw) == expected


def test_sides_sort_in_pressing_order():
    """A record's sides must order A, B, C, D — not alphabetically by string."""
    raws = ["B1", "A2", "A1", "C1", "B2"]
    ordered = sorted(raws, key=lambda r: tuple(x or 0 for x in parse_position(r)))
    assert ordered == ["A1", "A2", "B1", "B2", "C1"]


def test_side_letter_round_trips():
    for raw in ("A1", "B2", "Z1", "AA1"):
        side, _ = parse_position(raw)
        assert raw.startswith(side_letter(side))


def test_a_non_side_position_never_claims_a_side():
    """'Digi 1' is a download code, not a side. It must not become side 4."""
    side, index = parse_position("Digi 1")
    assert side is None
    assert index == 1
