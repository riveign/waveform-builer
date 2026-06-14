"""Tests for the featured-artists soft bias (spec 021, Phase B)."""

from unittest.mock import MagicMock

from kiku.setbuilder.scoring import (
    _ARTIST_SPAN,
    artist_matches_any,
    artist_term,
    transition_score,
)


def _track(artist="Someone", key="8A", bpm=128.0, genre="techno", energy="mid"):
    t = MagicMock()
    t.id = 1
    t.artist = artist
    t.key = key
    t.bpm = bpm
    t.dir_genre = genre
    t.rb_genre = genre
    t.dir_energy = energy
    t.rating = 3
    t.play_count = 5
    t.kiku_play_count = 0
    t.playlist_tags = None
    # energy_fit reads audio_features then resolved_energy_zone — give it real values
    t.audio_features = None
    t.resolved_energy_zone = ("build", "dir_energy", 0.8)
    return t


# ── artist_matches_any ──
def test_matches_any_direct():
    assert artist_matches_any("Bicep", ["Bicep"]) is True


def test_matches_any_collaboration():
    # Collaboration is matched via the token matcher.
    assert artist_matches_any("Bicep & Chroma", ["Bicep"]) is True


def test_matches_any_no_match():
    assert artist_matches_any("Four Tet", ["Bicep"]) is False


def test_matches_any_empty_list():
    assert artist_matches_any("Bicep", []) is False
    assert artist_matches_any("Bicep", None) is False


# ── artist_term ──
def test_term_off_when_intensity_zero():
    contrib, bd = artist_term(_track("Bicep"), ["Bicep"], 0.0)
    assert contrib == 0.0
    assert bd is None


def test_term_off_when_no_preferred():
    contrib, bd = artist_term(_track("Bicep"), None, 0.5)
    assert contrib == 0.0
    assert bd is None


def test_term_zero_on_non_match():
    contrib, bd = artist_term(_track("Four Tet"), ["Bicep"], 0.5)
    assert contrib == 0.0
    assert bd is None


def test_term_positive_on_match():
    contrib, bd = artist_term(_track("Bicep"), ["Bicep"], 0.5)
    assert contrib > 0.0
    assert bd is not None
    assert bd["matched"] is True


def test_term_scales_with_intensity():
    low, _ = artist_term(_track("Bicep"), ["Bicep"], 0.25)
    high, _ = artist_term(_track("Bicep"), ["Bicep"], 0.75)
    assert high > low


def test_term_bounded_by_span():
    contrib, _ = artist_term(_track("Bicep"), ["Bicep"], 1.0)
    assert contrib == _ARTIST_SPAN


def test_term_collaboration_matches():
    contrib, _ = artist_term(_track("Bicep & Chroma"), ["Bicep"], 1.0)
    assert contrib == _ARTIST_SPAN


# ── transition_score integration ──
def test_transition_higher_with_preferred_artist():
    frm = _track("Origin")
    to = _track("Bicep")
    baseline = transition_score(frm, to)
    boosted = transition_score(frm, to, preferred_artists=["Bicep"], artist_intensity=0.8)
    assert boosted > baseline


def test_transition_identical_at_intensity_zero():
    frm = _track("Origin")
    to = _track("Bicep")
    baseline = transition_score(frm, to)
    same = transition_score(frm, to, preferred_artists=["Bicep"], artist_intensity=0.0)
    assert same == baseline


def test_transition_unaffected_for_non_preferred():
    # Soft bias only — a non-preferred track scores the same with or without prefs.
    frm = _track("Origin")
    to = _track("Four Tet")
    baseline = transition_score(frm, to)
    same = transition_score(frm, to, preferred_artists=["Bicep"], artist_intensity=0.8)
    assert same == baseline


# ── Planner-level soft-bias contract ──
def _seeded_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from kiku.db.models import Base, Track

    # StaticPool keeps a single shared connection so the in-memory schema
    # persists across the create_all → insert → query calls below.
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    for i in range(1, 21):
        session.add(Track(
            id=i,
            title=f"Track {i}",
            artist="Bicep" if i <= 3 else f"Artist {i}",
            bpm=126.0 + (i % 5),
            key="8A" if i % 2 == 0 else "8B",
            dir_genre="techno",
            dir_energy="mid",
            duration_sec=360.0,
            rating=3,
            play_count=i,
        ))
    session.commit()
    return session


def test_planner_pool_not_filtered_by_preferred_artists():
    """Preferred artists tilt scoring but never narrow the candidate pool."""
    from kiku.setbuilder.planner import build_set

    session = _seeded_session()
    result = build_set(
        session=session,
        duration_min=30,
        set_name="Artist Bias Test",
        preferred_artists=["Bicep"],
        artist_intensity=0.8,
    )
    assert result is not None
    artists = {st.track.artist for st in result.tracks}
    # The set leans toward Bicep but is NOT all-Bicep — other artists remain eligible.
    assert any(a != "Bicep" for a in artists)
