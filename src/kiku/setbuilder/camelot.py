"""Harmonic mixing engine using the Camelot wheel."""

from __future__ import annotations

import re

# Camelot wheel: 12 positions, A (minor) and B (major)
# Adjacent = +/-1 on the wheel number, or A<->B at same number

_CAMELOT_RE = re.compile(r"^(\d{1,2})([AB])$", re.IGNORECASE)

# Standard key notation to Camelot mapping
_KEY_TO_CAMELOT = {
    # Minor keys (A = minor)
    "Abm": "1A",
    "G#m": "1A",
    "Ebm": "2A",
    "D#m": "2A",
    "Bbm": "3A",
    "A#m": "3A",
    "Fm": "4A",
    "Cm": "5A",
    "Gm": "6A",
    "Dm": "7A",
    "Am": "8A",
    "Em": "9A",
    "Bm": "10A",
    "F#m": "11A",
    "Gbm": "11A",
    "Dbm": "12A",
    "C#m": "12A",
    # Major keys (B = major)
    "B": "1B",
    "Cb": "1B",
    "F#": "2B",
    "Gb": "2B",
    "Db": "3B",
    "C#": "3B",
    "Ab": "4B",
    "G#": "4B",
    "Eb": "5B",
    "D#": "5B",
    "Bb": "6B",
    "A#": "6B",
    "F": "7B",
    "C": "8B",
    "G": "9B",
    "D": "10B",
    "A": "11B",
    "E": "12B",
}


def parse_camelot(key: str | None) -> tuple[int, str] | None:
    """Parse Camelot or standard key notation into (number, letter)."""
    if not key:
        return None
    key = key.strip()

    # Try Camelot notation first (e.g. '8A')
    m = _CAMELOT_RE.match(key)
    if m:
        num = int(m.group(1))
        letter = m.group(2).upper()
        if 1 <= num <= 12:
            return (num, letter)
        return None

    # Try standard key notation (e.g. 'Am', 'F#', 'Ebm')
    camelot = _KEY_TO_CAMELOT.get(key)
    if camelot:
        m = _CAMELOT_RE.match(camelot)
        if m:
            return (int(m.group(1)), m.group(2).upper())

    return None


def harmonic_score(key_a: str | None, key_b: str | None) -> float:
    """Score harmonic compatibility between two Camelot keys.

    Returns:
        1.0  — same key
        0.85 — adjacent on wheel (+/-1)
        0.8  — major/minor switch (same number, A<->B)
        0.5  — +/-2 on wheel
        0.2  — everything else
    """
    ca = parse_camelot(key_a)
    cb = parse_camelot(key_b)

    if ca is None or cb is None:
        return 0.5  # Unknown key — neutral score

    num_a, let_a = ca
    num_b, let_b = cb

    # Same key
    if num_a == num_b and let_a == let_b:
        return 1.0

    # Major/minor switch at same position
    if num_a == num_b and let_a != let_b:
        return 0.8

    # Adjacent on wheel (handles wrap: 12 -> 1)
    diff = abs(num_a - num_b)
    wheel_diff = min(diff, 12 - diff)

    if wheel_diff == 1 and let_a == let_b:
        return 0.85

    if wheel_diff == 2 and let_a == let_b:
        return 0.5

    # Adjacent + mode switch
    if wheel_diff == 1 and let_a != let_b:
        return 0.6

    return 0.2


# ── Directional move vocabulary (reused by slot_picks + the API/CLI) ──

_INTENT_ENERGY_DELTA = {
    "push_higher": 0.15,
    "brighten": 0.05,
    "cool_down": -0.15,
    "hold": 0.0,
}


def camelot_str(key: tuple[int, str]) -> str:
    """Format a ``(number, letter)`` Camelot key as its canonical string.

    ``(9, "A") -> "9A"``.
    """
    num, letter = key
    return f"{num}{letter}"


def step_wheel(key: tuple[int, str], delta: int) -> tuple[int, str]:
    """Step ``delta`` positions around the 12-slot wheel, same letter.

    Wraps ``12 -> 1`` (up) and ``1 -> 12`` (down) so the number stays in 1..12.
    """
    num, letter = key
    stepped = ((num - 1 + delta) % 12) + 1
    return (stepped, letter)


def flip_mode(key: tuple[int, str]) -> tuple[int, str]:
    """Flip the mode ``A<->B`` at the same wheel number (minor<->major)."""
    num, letter = key
    return (num, "B" if letter == "A" else "A")


def move_targets(neighbor_key: str | None, intent: str) -> list[tuple[int, str]]:
    """Enumerate the target Camelot key(s) for a named move, relative to a neighbor.

    ``push_higher`` -> ``[+1 same letter]``            (8A -> 9A)
    ``brighten``    -> ``[mode flip]``                 (8A -> 8B)
    ``cool_down``   -> ``[-1 same letter]`` (+ B->A)   (8A -> 7A ; 8B -> 7B and 8A)
    ``hold``        -> ``[]``  (no key constraint)

    Returns ``[]`` for an unparseable neighbor or an unknown intent.
    """
    base = parse_camelot(neighbor_key)
    if base is None or intent == "hold":
        return []
    if intent == "push_higher":
        return [step_wheel(base, 1)]
    if intent == "brighten":
        return [flip_mode(base)]
    if intent == "cool_down":
        targets = [step_wheel(base, -1)]
        if base[1] == "B":
            targets.append(flip_mode(base))
        return targets
    return []


def intent_allowed_keys(neighbor_key: str | None, intent: str) -> set[str] | None:
    """Map a named intent to the allowed candidate-key set, relative to a neighbor.

    Returns ``None`` for ``hold`` (no key filter) or when no targets can be
    derived (unparseable neighbor / unknown intent) — i.e. no hard filter.
    """
    targets = move_targets(neighbor_key, intent)
    if not targets:
        return None
    return {camelot_str(t) for t in targets}


def intent_energy_delta(intent: str) -> float:
    """Energy-target shift a named intent applies to the smooth baseline."""
    return _INTENT_ENERGY_DELTA.get(intent, 0.0)
