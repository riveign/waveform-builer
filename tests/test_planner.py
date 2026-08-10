"""Invariants for planner.py — the beam search that builds a set.

A badly built set still looks like a set: the tracks are real, the order is
plausible, and nothing raises. That is exactly why these are the hardest defects
in Kiku to notice by eye (docs/notes/CLM-003/R6), and why the assertions here are
properties that must hold for any library rather than one expected tracklist.

Two of them encode product rules that the set-role and artist work went out of
its way to establish, and which a future scoring tweak could quietly break:
a soft bias must never become a filter, and the artist cooldown outranks it.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.config import ARTIST_COOLDOWN
from kiku.db.models import Base, Track
from kiku.setbuilder.constraints import parse_energy_string
from kiku.setbuilder.planner import _violates_artist_cooldown, build_set

PROFILE = "warmup:20:0.3,build:20:0.6,peak:20:0.9,cooldown:20:0.4"

KEYS = ["8A", "9A", "8B", "5A", "12A", "3A", "7A", "10A", "4A", "11A"]
ENERGIES = ["warmup", "build", "peak", "drive", "close"]


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'p.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture()
def library(session):
    """A library wide enough that the planner has real choices to make.

    30 tracks over 10 artists, so the 5-track artist cooldown is satisfiable but
    not automatic.
    """
    for i in range(1, 31):
        session.add(
            Track(
                id=i,
                title=f"Track {i}",
                artist=f"Artist {i % 10}",
                bpm=120.0 + (i % 12),
                key=KEYS[i % len(KEYS)],
                dir_genre="techno" if i % 2 else "house",
                dir_energy=ENERGIES[i % len(ENERGIES)],
                duration_sec=360.0,
                rating=3,
            )
        )
    session.commit()
    return session


def _seq(built) -> list[Track]:
    return [st.track for st in sorted(built.tracks, key=lambda st: st.position)]


# ── A set must never contain the same track twice ──────────────────────────


def test_never_repeats_a_track(library):
    built = build_set(library, duration_min=90, energy_profile=parse_energy_string(PROFILE))

    assert built is not None
    ids = [t.id for t in _seq(built)]
    assert len(ids) == len(set(ids)), f"a track appears more than once: {ids}"


def test_positions_are_contiguous_from_zero(library):
    """The UI, the exporters and the reorder diff all index by position."""
    built = build_set(library, duration_min=90, energy_profile=parse_energy_string(PROFILE))

    positions = sorted(st.position for st in built.tracks)
    assert positions == list(range(len(positions)))


# ── The artist cooldown is a rule, not a preference ────────────────────────


def test_no_artist_repeats_inside_the_cooldown_window(library):
    built = build_set(library, duration_min=120, energy_profile=parse_energy_string(PROFILE))
    seq = _seq(built)

    for i, track in enumerate(seq):
        window = seq[max(0, i - ARTIST_COOLDOWN) : i]
        clashes = [t for t in window if t.artist and t.artist == track.artist]
        assert not clashes, (
            f"{track.artist!r} repeats at position {i} within {ARTIST_COOLDOWN} slots"
        )


def test_cooldown_check_looks_only_at_the_recent_window():
    a = Track(id=1, title="x", artist="Repeat")
    others = [Track(id=i, title="x", artist=f"Other {i}") for i in range(2, 2 + ARTIST_COOLDOWN)]

    assert _violates_artist_cooldown([a], a) is True
    assert _violates_artist_cooldown([a, *others], a) is False, (
        "the artist has aged out of the window and should be allowed again"
    )


def test_cooldown_ignores_tracks_with_no_artist():
    """Unknown artists must not all collide with each other."""
    unknown = Track(id=1, title="x", artist=None)
    assert _violates_artist_cooldown([unknown], unknown) is False


# ── Soft biases must never become filters ──────────────────────────────────


def test_preferred_artists_bias_does_not_filter_the_pool(library):
    """Spec: featured artists are a nudge during scoring, never a filter. At full
    intensity the set must still be free to use everyone else — otherwise the
    cooldown would be unsatisfiable and the DJ's library invisible."""
    built = build_set(
        library,
        duration_min=120,
        energy_profile=parse_energy_string(PROFILE),
        preferred_artists=["Artist 1"],
        artist_intensity=1.0,
    )
    artists = {t.artist for t in _seq(built)}

    assert len(artists) > 1, f"the bias behaved as a filter: only {artists}"


def test_opener_role_bias_does_not_filter_the_pool(library):
    """Same rule for set roles (spec 028): tagging one track `opener` must not
    restrict the set to tagged tracks."""
    first = library.get(Track, 3)
    first.set_roles = json.dumps(["opener"])
    library.commit()

    built = build_set(library, duration_min=90, energy_profile=parse_energy_string(PROFILE))
    seq = _seq(built)

    assert len(seq) > 1
    untagged = [t for t in seq if not t.set_roles]
    assert untagged, "role bias behaved as a filter — every track was tagged"


# ── Genre, by contrast, IS a hard filter ───────────────────────────────────


def test_genre_filter_is_hard(library):
    """The distinction matters: genres are what the DJ excluded on purpose,
    roles and artists are what they leaned toward."""
    built = build_set(
        library,
        duration_min=90,
        energy_profile=parse_energy_string(PROFILE),
        genres=["techno"],
    )

    assert built is not None
    for t in _seq(built):
        assert "techno" in (t.dir_genre or "").lower()


# ── Duration and degenerate libraries ──────────────────────────────────────


def test_set_reaches_roughly_the_requested_duration(library):
    """Beam search stops once elapsed crosses the target, so the set should land
    at or just past it — never dramatically short."""
    target = 60
    built = build_set(library, duration_min=target, energy_profile=parse_energy_string(PROFILE))
    minutes = sum((t.duration_sec or 360) / 60 for t in _seq(built))

    assert minutes >= target * 0.8, f"set is only {minutes:.0f} min against a {target} target"


def test_empty_library_returns_none_rather_than_raising(session):
    assert build_set(session, duration_min=60, energy_profile=parse_energy_string(PROFILE)) is None


def test_library_smaller_than_the_target_still_produces_a_set(session):
    """Three tracks cannot fill two hours. The planner must stop, not loop."""
    for i in range(1, 4):
        session.add(
            Track(
                id=i,
                title=f"T{i}",
                artist=f"A{i}",
                bpm=124.0,
                key="8A",
                dir_energy="build",
                duration_sec=360.0,
            )
        )
    session.commit()

    built = build_set(session, duration_min=120, energy_profile=parse_energy_string(PROFILE))

    assert built is not None
    ids = [t.id for t in _seq(built)]
    assert len(ids) == len(set(ids)), "ran out of tracks and started repeating"
    assert len(ids) <= 3
