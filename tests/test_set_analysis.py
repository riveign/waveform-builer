"""Tests for set analysis — teaching moments, arc classification, energy inference."""

from kiku.analysis.teaching import (
    detect_set_patterns,
    transition_teaching_moment,
)
from kiku.analysis.set_analyzer import (
    _classify_bpm_style,
    _classify_energy_shape,
    _classify_key_style,
    _detect_genre_segments,
)
from unittest.mock import MagicMock


# ── Teaching Moments ───────────────────────────────────────────────────


def test_strong_transition_no_suggestion():
    """Strong transitions (>= 0.8) should celebrate and have no suggestion."""
    scores = {"harmonic": 0.85, "energy_fit": 0.9, "bpm_compat": 0.95,
              "genre_coherence": 0.8, "track_quality": 0.7, "total": 0.85}
    moment, suggestion = transition_teaching_moment(
        scores, "8A", "8A", 128.0, 128.0, "Techno", "Techno"
    )
    assert suggestion is None
    assert "Your ear picked this" in moment


def test_strong_same_key():
    """Same key should mention the key in the teaching moment."""
    scores = {"harmonic": 1.0, "energy_fit": 0.8, "bpm_compat": 0.9,
              "genre_coherence": 0.8, "track_quality": 0.7, "total": 0.88}
    moment, _ = transition_teaching_moment(
        scores, "8A", "8A", 128.0, 130.0, "Techno", "Techno"
    )
    assert "8A" in moment


def test_good_transition_may_suggest():
    """Good transitions (0.6-0.8) may get a suggestion if a dimension is weak."""
    scores = {"harmonic": 0.3, "energy_fit": 0.8, "bpm_compat": 0.9,
              "genre_coherence": 0.8, "track_quality": 0.7, "total": 0.68}
    moment, suggestion = transition_teaching_moment(
        scores, "1A", "6B", 128.0, 130.0, "Techno", "Techno"
    )
    assert moment  # non-empty
    assert suggestion is not None  # harmonic is < 0.5


def test_weak_transition_has_suggestion():
    """Weak transitions (< 0.6) should always get a suggestion."""
    scores = {"harmonic": 0.2, "energy_fit": 0.3, "bpm_compat": 0.4,
              "genre_coherence": 0.3, "track_quality": 0.5, "total": 0.32}
    moment, suggestion = transition_teaching_moment(
        scores, "1A", "6B", 100.0, 140.0, "Techno", "Trance"
    )
    assert moment
    assert suggestion is not None


def test_weak_bpm_mentions_percentage():
    """When BPM is the weakest dimension, the moment should mention the jump."""
    scores = {"harmonic": 0.8, "energy_fit": 0.7, "bpm_compat": 0.1,
              "genre_coherence": 0.6, "track_quality": 0.5, "total": 0.45}
    moment, _ = transition_teaching_moment(
        scores, "8A", "8A", 100.0, 140.0, "Techno", "Techno"
    )
    assert "%" in moment


def test_weak_genre_mentions_families():
    """When genre is weakest, the moment should mention genre families."""
    scores = {"harmonic": 0.8, "energy_fit": 0.7, "bpm_compat": 0.8,
              "genre_coherence": 0.1, "track_quality": 0.5, "total": 0.45}
    moment, _ = transition_teaching_moment(
        scores, "8A", "8A", 128.0, 128.0, "Techno", "Indie Dance"
    )
    assert "genre" in moment.lower() or "Techno" in moment or "Other" in moment


# ── Set Patterns ───────────────────────────────────────────────────────


def test_detect_patterns_building_energy():
    """Should detect a building energy arc."""
    transitions = [{"harmonic": 0.8, "energy_fit": 0.7, "bpm_compat": 0.8, "genre_coherence": 0.8}]
    energy_curve = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    patterns = detect_set_patterns(transitions, energy_curve, [], [])
    assert any("build" in p.lower() for p in patterns)


def test_detect_patterns_steady_energy():
    """Should detect flat/steady energy."""
    transitions = [{"harmonic": 0.8, "energy_fit": 0.7, "bpm_compat": 0.8, "genre_coherence": 0.8}]
    energy_curve = [0.5, 0.52, 0.48, 0.51, 0.49, 0.5]
    patterns = detect_set_patterns(transitions, energy_curve, [], [])
    assert any("steady" in p.lower() for p in patterns)


def test_detect_patterns_strong_dimension():
    """Should celebrate the strongest scoring dimension."""
    transitions = [
        {"harmonic": 0.9, "energy_fit": 0.5, "bpm_compat": 0.5, "genre_coherence": 0.5},
        {"harmonic": 0.85, "energy_fit": 0.4, "bpm_compat": 0.6, "genre_coherence": 0.5},
    ]
    patterns = detect_set_patterns(transitions, [0.5, 0.5, 0.5], [], [])
    assert any("key relationships" in p for p in patterns)


def test_detect_patterns_empty():
    """Empty transitions should return no patterns."""
    assert detect_set_patterns([], [], [], []) == []


# ── Energy Shape Classification ────────────────────────────────────────


def test_energy_shape_flat():
    assert _classify_energy_shape([0.5, 0.52, 0.48, 0.51]) == "flat"


def test_energy_shape_ramp_up():
    assert _classify_energy_shape([0.3, 0.4, 0.5, 0.6, 0.7, 0.8]) == "ramp-up"


def test_energy_shape_wind_down():
    # Peak at index 4 (>= 40%) so peak-valley check doesn't trigger
    assert _classify_energy_shape([0.5, 0.55, 0.5, 0.7, 0.75, 0.7, 0.5, 0.4, 0.35, 0.3]) == "wind-down"


def test_energy_shape_too_short():
    assert _classify_energy_shape([0.5]) == "too-short"


# ── Key Style ──────────────────────────────────────────────────────────


def test_key_style_home_key():
    assert _classify_key_style(["8A", "8A", "8A", "8A", "8A"]) == "home-key"


def test_key_style_adventurous():
    assert _classify_key_style(["1A", "3B", "5A", "7B", "9A", "11B", "2A"]) == "adventurous"


def test_key_style_unknown():
    assert _classify_key_style([None, None]) == "unknown"


def test_key_style_chromatic_walk():
    assert _classify_key_style(["8A", "8A", "9A", "9A", "10A"]) == "chromatic-walk"


# ── BPM Style ─────────────────────────────────────────────────────────


def test_bpm_steady():
    assert _classify_bpm_style([128.0, 128.5, 127.8, 128.2]) == "steady"


def test_bpm_gradual_build():
    assert _classify_bpm_style([120.0, 122.0, 125.0, 128.0, 132.0]) == "gradual-build"


def test_bpm_volatile():
    assert _classify_bpm_style([120.0, 140.0, 118.0, 135.0, 121.0]) == "volatile"


def test_bpm_unknown():
    assert _classify_bpm_style([128.0]) == "unknown"


# ── Genre Segments ─────────────────────────────────────────────────────


def _mock_track(genre: str | None) -> MagicMock:
    t = MagicMock()
    t.dir_genre = genre
    t.rb_genre = genre
    return t


def test_genre_segments_single():
    tracks = [_mock_track("Techno"), _mock_track("Hard Techno"), _mock_track("Techno")]
    segs = _detect_genre_segments(tracks)
    assert len(segs) == 1
    assert segs[0]["genre_family"] == "techno"


def test_genre_segments_transition():
    tracks = [_mock_track("Techno"), _mock_track("Techno"), _mock_track("Deep House"), _mock_track("House")]
    segs = _detect_genre_segments(tracks)
    assert len(segs) == 2
    assert segs[0]["genre_family"] == "techno"
    assert segs[1]["genre_family"] == "house"
