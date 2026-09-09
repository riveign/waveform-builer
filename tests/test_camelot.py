"""Tests for Camelot wheel harmonic scoring."""

from kiku.setbuilder.camelot import (
    camelot_str,
    flip_mode,
    harmonic_score,
    intent_allowed_keys,
    intent_energy_delta,
    key_spellings,
    move_targets,
    parse_camelot,
    step_wheel,
)


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


def test_camelot_str():
    assert camelot_str((9, "A")) == "9A"
    assert camelot_str((12, "B")) == "12B"


def test_step_wheel_wrap():
    assert step_wheel((8, "A"), 1) == (9, "A")
    assert step_wheel((8, "A"), -1) == (7, "A")
    assert step_wheel((12, "A"), 1) == (1, "A")  # wrap up
    assert step_wheel((1, "A"), -1) == (12, "A")  # wrap down


def test_flip_mode():
    assert flip_mode((8, "A")) == (8, "B")
    assert flip_mode((8, "B")) == (8, "A")


def test_move_targets_push_higher():
    assert move_targets("8A", "push_higher") == [(9, "A")]
    assert move_targets("12A", "push_higher") == [(1, "A")]  # wheel wrap


def test_move_targets_brighten():
    assert move_targets("8A", "brighten") == [(8, "B")]


def test_move_targets_cool_down():
    assert move_targets("8A", "cool_down") == [(7, "A")]
    assert set(move_targets("8B", "cool_down")) == {(7, "B"), (8, "A")}


def test_move_targets_hold_and_unparseable():
    assert move_targets("8A", "hold") == []
    assert move_targets(None, "push_higher") == []
    assert move_targets("nonsense", "push_higher") == []


def test_intent_allowed_keys():
    assert intent_allowed_keys("8A", "push_higher") == {"9A"}
    assert intent_allowed_keys("8A", "brighten") == {"8B"}
    assert intent_allowed_keys("8B", "cool_down") == {"7B", "8A"}
    assert intent_allowed_keys("8A", "hold") is None
    assert intent_allowed_keys(None, "push_higher") is None


def test_intent_energy_delta():
    assert intent_energy_delta("push_higher") == 0.15
    assert intent_energy_delta("brighten") == 0.05
    assert intent_energy_delta("cool_down") == -0.15
    assert intent_energy_delta("hold") == 0.0


def test_key_spellings_bridges_notations():
    """One wheel position, every spelling the library might have stored."""
    assert key_spellings("8A") == {"8A", "Am"}
    assert key_spellings("Am") == {"8A", "Am"}
    assert key_spellings("1A") == {"1A", "Abm", "G#m"}
    assert key_spellings("A") == {"11B", "A"}


def test_key_spellings_keeps_unplaceable_keys():
    assert key_spellings("weird") == {"weird"}
    assert key_spellings(None) == set()
    assert key_spellings("  ") == set()
