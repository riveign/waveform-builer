"""Tests for the filename-prefix track-number fallback parser."""

from __future__ import annotations

import pytest

from kiku.db.filename_track_numbers import parse_track_position


@pytest.mark.parametrize(
    "filename,expected",
    [
        # Disc-track form: dd-tt
        ("01-18 Title.flac", (1, 18)),
        ("02-05 Some Track.mp3", (2, 5)),
        ("/path/to/01-09 With Dir.flac", (1, 9)),
        # Disc-track with underscore separator between disc and track
        ("01_09 Track.flac", (1, 9)),
        # Track-only form: leading number
        ("09 - Title.flac", (None, 9)),
        ("12 Track Name.mp3", (None, 12)),
        ("07.Some Track.flac", (None, 7)),
        # Single-digit track is fine
        ("1 Intro.wav", (None, 1)),
        # No prefix
        ("Track Name.flac", (None, None)),
        ("Artist - Title.mp3", (None, None)),
        # Empty / blank
        ("", (None, None)),
        # Pure numbers without separator are not track numbers
        ("123456.flac", (None, None)),
        # Out of range (>99 disc) should fall through to track-only path
        # but 100 doesn't match \d{1,2}, so it returns (None, None)
        ("100 Foo.flac", (None, None)),
    ],
)
def test_parse_track_position(filename: str, expected: tuple) -> None:
    assert parse_track_position(filename) == expected


def test_parse_track_position_zero_track_rejected() -> None:
    """A leading '00' should be rejected (track 0 isn't valid)."""
    assert parse_track_position("00 Hidden.flac") == (None, None)


def test_parse_track_position_strips_dirs() -> None:
    """Only the basename matters; parent directories should be ignored."""
    assert parse_track_position("/Volumes/SSD/Musica/Album/03 Track.flac") == (
        None,
        3,
    )
