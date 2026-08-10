"""Invariants for reorder.py — the module that changes the order of a played set.

Reordering is the easiest place in Kiku to lose or duplicate a track without
anyone noticing, because the result still *looks* like a set. These tests assert
the properties that must hold for any input rather than checking one fixed
answer, which is the only way to catch that class of bug (docs/notes/CLM-003/R6).

`optimize_full` is a simulated annealer and therefore random; every test here
either seeds the RNG or asserts something true of all outcomes.
"""

from __future__ import annotations

import random

import pytest

from kiku.db.models import Track
from kiku.setbuilder.constraints import parse_energy_string
from kiku.setbuilder.reorder import (
    get_energy_curve,
    optimize_full,
    optimize_gentle,
    score_full_sequence,
)

KEYS = ["8A", "9A", "8B", "5A", "12A", "3A", "7A", "10A"]
GENRES = ["techno", "house", "techno", "trance", "house", "techno", "breaks", "house"]
ENERGIES = ["warmup", "build", "peak", "drive", "peak", "build", "close", "warmup"]


def _track(i: int) -> Track:
    """A detached Track. Reorder is pure — it never touches the session."""
    return Track(
        id=i,
        title=f"T{i}",
        artist=f"Artist {i % 4}",
        bpm=120.0 + (i * 3 % 20),
        key=KEYS[i % len(KEYS)],
        dir_genre=GENRES[i % len(GENRES)],
        dir_energy=ENERGIES[i % len(ENERGIES)],
        duration_sec=360.0,
    )


@pytest.fixture()
def tracks() -> list[Track]:
    return [_track(i) for i in range(1, 13)]


@pytest.fixture()
def profile():
    return parse_energy_string("warmup:30:0.3,build:40:0.6,peak:40:0.9,cooldown:20:0.4")


def _ids(ts: list[Track]) -> list[int]:
    return [t.id for t in ts]


# ── The core invariant: reordering is a permutation ────────────────────────


@pytest.mark.parametrize("optimizer", [optimize_gentle, optimize_full])
def test_result_is_a_permutation_of_the_input(optimizer, tracks, profile):
    """No track may be lost, duplicated, or invented. This is the whole game."""
    random.seed(1234)
    result, _ = optimizer(tracks, profile)

    assert len(result) == len(tracks), "track count changed"
    assert sorted(_ids(result)) == sorted(_ids(tracks)), "the multiset of tracks changed"
    assert len(set(_ids(result))) == len(result), "a track appears twice"


@pytest.mark.parametrize("optimizer", [optimize_gentle, optimize_full])
def test_never_returns_a_worse_arrangement(optimizer, tracks, profile):
    """Both optimizers keep the best sequence they saw, so the score cannot fall."""
    random.seed(99)
    before = score_full_sequence(tracks, profile)
    result, _ = optimizer(tracks, profile)
    after = score_full_sequence(result, profile)

    assert after >= before - 1e-9, f"score fell from {before:.4f} to {after:.4f}"


@pytest.mark.parametrize("optimizer", [optimize_gentle, optimize_full])
@pytest.mark.parametrize("n", [0, 1])
def test_sets_too_small_to_reorder_pass_through(optimizer, n, profile):
    """Nothing to optimise below two tracks, so the order must be left alone and
    no change reported. A newly created set goes through here."""
    small = [_track(i) for i in range(n)]
    result, changes = optimizer(small, profile)

    assert _ids(result) == _ids(small)
    assert changes == []


@pytest.mark.parametrize("optimizer", [optimize_gentle, optimize_full])
def test_a_two_track_set_may_swap_but_stays_a_permutation(optimizer, profile):
    """Two tracks is one real transition, so swapping is legitimate — but the pair
    itself must survive."""
    random.seed(7)
    pair = [_track(1), _track(2)]
    result, _ = optimizer(pair, profile)

    assert sorted(_ids(result)) == [1, 2]


def test_gentle_is_deterministic(tracks, profile):
    """Hill-climbing has no RNG, so the same set must reorder the same way twice."""
    a, _ = optimize_gentle(tracks, profile)
    b, _ = optimize_gentle(tracks, profile)

    assert _ids(a) == _ids(b)


def test_full_is_a_permutation_under_any_seed(tracks, profile):
    """The annealer's randomness must never be able to corrupt the track set."""
    for seed in range(8):
        random.seed(seed)
        result, _ = optimize_full(tracks, profile, iterations=300)
        assert sorted(_ids(result)) == sorted(_ids(tracks)), f"seed {seed} lost a track"


# ── Reported changes must describe what actually happened ──────────────────


def test_changes_match_the_tracks_that_actually_moved(tracks, profile):
    """A change list that disagrees with the result is worse than no change list:
    the DJ is told a move happened that did not."""
    result, changes = optimize_gentle(tracks, profile)

    original = {t.id: i for i, t in enumerate(tracks)}
    final = {t.id: i for i, t in enumerate(result)}
    actually_moved = {tid for tid in original if original[tid] != final[tid]}
    reported = {c.track_id for c in changes}

    assert reported == actually_moved


def test_changes_carry_the_real_positions(tracks, profile):
    result, changes = optimize_gentle(tracks, profile)
    final = {t.id: i for i, t in enumerate(result)}

    for c in changes:
        assert c.to_position == final[c.track_id]
        assert c.from_position != c.to_position


# ── Scoring ────────────────────────────────────────────────────────────────


def test_score_of_a_trivial_sequence_is_defined(profile):
    """Fewer than two tracks means no transitions to score; 1.0 by convention."""
    assert score_full_sequence([], profile) == 1.0
    assert score_full_sequence([_track(1)], profile) == 1.0


def test_genre_fragmentation_is_penalised(profile):
    """Oscillating between families should score below clustering them, which is
    what stops the optimizer producing a technically-harmonic mess."""
    clustered = [_track(i) for i in (1, 3, 6, 2, 5, 8)]  # techno-ish then house-ish
    for t, g in zip(clustered, ["techno", "techno", "techno", "house", "house", "house"]):
        t.dir_genre = g

    oscillating = [_track(i) for i in (1, 3, 6, 2, 5, 8)]
    for t, g in zip(oscillating, ["techno", "house", "techno", "house", "techno", "house"]):
        t.dir_genre = g

    assert score_full_sequence(clustered, profile) > score_full_sequence(oscillating, profile)


# ── Energy curve ───────────────────────────────────────────────────────────


def test_energy_curve_has_one_point_per_track(tracks, profile):
    curve = get_energy_curve(tracks, profile)
    assert len(curve) == len(tracks)


def test_energy_curve_is_empty_for_an_empty_set(profile):
    assert get_energy_curve([], profile) == []
