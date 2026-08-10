"""Invariants for filler.py — proposing tracks to patch gaps in a manual set.

The filler is a generator of SSE events rather than a function returning a list,
so its contract is a *sequence*: it must always open, always close, and never
propose something the set already contains. A duplicate here is invisible until
the DJ is on stage and plays the same record twice.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.db.models import Base, Set, SetTrack, Track
from kiku.setbuilder.constraints import parse_energy_string
from kiku.setbuilder.filler import fill_set

PROFILE = "warmup:20:0.3,build:20:0.6,peak:20:0.9,cooldown:20:0.4"

# Deliberately clashing keys so the seeded set has poor transitions and the
# filler has real gaps to find.
CLASHING = ["8A", "3B", "11A", "6B", "1A", "9B"]


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'f.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture()
def seeded(session):
    """A 6-track set with bad transitions, plus 24 unused candidates."""
    for i in range(1, 31):
        session.add(
            Track(
                id=i,
                title=f"Track {i}",
                artist=f"Artist {i % 10}",
                bpm=124.0 + (i % 6),
                key=CLASHING[i % len(CLASHING)] if i <= 6 else f"{(i % 12) + 1}A",
                dir_genre="techno",
                dir_energy=["warmup", "build", "peak", "drive", "close"][i % 5],
                duration_sec=360.0,
                rating=3,
            )
        )
    s = Set(id=1, name="Gappy", duration_min=60, energy_profile=PROFILE)
    session.add(s)
    session.flush()
    for pos, tid in enumerate(range(1, 7)):
        session.add(SetTrack(set_id=1, position=pos, track_id=tid))
    session.commit()
    return session


def _events(session, **kwargs) -> list:
    profile = parse_energy_string(PROFILE)
    return list(fill_set(session, 1, energy_profile=profile, **kwargs))


def _of(events, kind: str) -> list:
    return [e for e in events if e.event == kind]


# ── The event stream is a contract ─────────────────────────────────────────


def test_stream_opens_and_closes(seeded):
    events = _events(seeded)

    assert events[0].event == "fill_started"
    assert events[-1].event == "fill_complete"


def test_missing_set_yields_one_error_and_stops(session):
    events = list(fill_set(session, 999))

    assert len(events) == 1
    assert events[0].event == "error"


def test_empty_set_yields_an_error_rather_than_proposing_blind(session):
    session.add(Set(id=1, name="Empty", duration_min=60))
    session.commit()

    events = list(fill_set(session, 1))

    assert [e.event for e in events] == ["error"]


# ── Never propose a track the set already has ──────────────────────────────


def test_never_proposes_a_track_already_in_the_set(seeded):
    events = _events(seeded)
    in_set = set(range(1, 7))

    for e in _of(events, "fill_proposed"):
        assert e.data["track_id"] not in in_set, (
            f"proposed track {e.data['track_id']}, which is already in the set"
        )


def test_never_proposes_the_same_track_twice(seeded):
    events = _events(seeded)
    proposed = [e.data["track_id"] for e in _of(events, "fill_proposed")]

    assert len(proposed) == len(set(proposed)), f"duplicate proposals: {proposed}"


def test_respects_the_artist_cooldown_against_the_existing_set(seeded):
    """A proposal that clashes with an artist already in the set is as wrong as a
    duplicate — the cooldown is a rule, not a preference (see test_planner)."""
    events = _events(seeded)
    existing_artists = {f"Artist {i % 10}" for i in range(1, 7)}

    for e in _of(events, "fill_proposed"):
        assert e.data["track_artist"] not in existing_artists


# ── Bounds ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("cap", [0, 1, 3])
def test_never_exceeds_max_fill_tracks(seeded, cap):
    events = _events(seeded, max_fill_tracks=cap)

    assert len(_of(events, "fill_proposed")) <= cap


def test_reported_count_matches_the_proposals_emitted(seeded):
    """The completion event drives the UI's summary, so it must not disagree with
    the stream the UI just rendered."""
    events = _events(seeded)
    complete = _of(events, "fill_complete")[0]

    assert complete.data["proposals_count"] == len(_of(events, "fill_proposed"))


def test_a_higher_gap_threshold_finds_at_least_as_many_gaps(seeded):
    """The threshold is 'how bad must a transition be to count as a gap', so
    raising it can only widen the net. A regression that inverted the comparison
    would show up here."""
    lenient = _of(_events(seeded, gap_threshold=0.95), "gap_identified")
    strict = _of(_events(seeded, gap_threshold=0.2), "gap_identified")

    assert len(lenient) >= len(strict)


# ── Proposals land where the gap is ────────────────────────────────────────


def test_every_proposal_sits_at_an_identified_gap(seeded):
    events = _events(seeded)
    gap_positions = {e.data["position"] for e in _of(events, "gap_identified")}

    for e in _of(events, "fill_proposed"):
        assert e.data["position"] in gap_positions


def test_proposal_positions_are_inside_the_set(seeded):
    events = _events(seeded)

    for e in _of(events, "fill_proposed"):
        assert 0 <= e.data["position"] <= 6


def test_proposals_carry_the_teaching_the_ui_shows(seeded):
    """Kiku's whole pitch is explaining why — a proposal with no explanation is a
    recommendation engine, which is what the product is explicitly not."""
    for e in _of(_events(seeded), "fill_proposed"):
        assert e.data["explanation"], "a proposal arrived with no explanation"
        assert e.data["breakdown"], "a proposal arrived with no score breakdown"
