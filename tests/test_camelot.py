"""Tests for Camelot wheel harmonic scoring."""

from kiku.setbuilder.camelot import harmonic_score, parse_camelot


def test_parse_camelot():
    assert parse_camelot("8A") == (8, "A")
    assert parse_camelot("12B") == (12, "B")
    assert parse_camelot("1a") == (1, "A")
    assert parse_camelot(None) is None
    assert parse_camelot("13A") is None
    assert parse_camelot("0A") is None


def test_same_key():
    assert harmonic_score("8A", "8A") == 1.0


def test_adjacent():
    assert harmonic_score("8A", "9A") == 0.85
    assert harmonic_score("8A", "7A") == 0.85
    # Wrap around
    assert harmonic_score("12A", "1A") == 0.85
    assert harmonic_score("1A", "12A") == 0.85


def test_major_minor_switch():
    assert harmonic_score("8A", "8B") == 0.8
    assert harmonic_score("8B", "8A") == 0.8


def test_two_steps():
    assert harmonic_score("8A", "10A") == 0.5
    assert harmonic_score("8A", "6A") == 0.5


def test_incompatible():
    assert harmonic_score("8A", "3A") == 0.2


def test_unknown_key():
    assert harmonic_score(None, "8A") == 0.5
    assert harmonic_score("8A", None) == 0.5
