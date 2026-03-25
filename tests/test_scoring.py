"""Tests for transition scoring."""

from unittest.mock import MagicMock

from kiku.setbuilder.scoring import bpm_compatibility, genre_coherence, track_quality


def test_bpm_same():
    assert bpm_compatibility(128.0, 128.0) == 1.0


def test_bpm_close():
    score = bpm_compatibility(128.0, 130.0)
    assert 0.7 < score < 1.0


def test_bpm_far():
    score = bpm_compatibility(128.0, 160.0)
    assert score < 0.3


def test_bpm_double():
    score = bpm_compatibility(70.0, 140.0)
    assert score >= 0.6


def test_bpm_unknown():
    assert bpm_compatibility(None, 128.0) == 0.5


def test_genre_same():
    assert genre_coherence("Techno", "Techno") == 1.0


def test_genre_family():
    assert genre_coherence("Techno", "Hard Techno") == 0.8
    assert genre_coherence("House", "Deep House") == 0.8


def test_genre_compatible_families():
    assert genre_coherence("Techno", "Hard Groove") == 0.5


def test_genre_incompatible():
    assert genre_coherence("Techno", "Post Punk") == 0.2


def test_genre_unknown():
    assert genre_coherence(None, "Techno") == 0.5


# ── track_quality tests ──


def _make_track(play_count=0, kiku_play_count=0, rating=3, playlist_tags=None):
    t = MagicMock()
    t.play_count = play_count
    t.kiku_play_count = kiku_play_count
    t.rating = rating
    t.playlist_tags = playlist_tags
    return t


def test_track_quality_neutral():
    """discovery_density=0 should return a score and no label."""
    t = _make_track(play_count=5, kiku_play_count=0, rating=4)
    score, label = track_quality(t, discovery_density=0.0)
    assert 0.0 <= score <= 1.0
    assert label is None


def test_track_quality_discovery_fresh_pick():
    """discovery_density=-1 with 0 plays should label 'fresh pick'."""
    t = _make_track(play_count=0, kiku_play_count=0, rating=3)
    score, label = track_quality(t, discovery_density=-1.0)
    assert label == "fresh pick"


def test_track_quality_discovery_rarely_played():
    """discovery_density=-0.5 with 3 plays should label 'rarely played'."""
    t = _make_track(play_count=2, kiku_play_count=1, rating=3)
    score, label = track_quality(t, discovery_density=-0.5)
    assert label == "rarely played"


def test_track_quality_density_battle_tested():
    """discovery_density=+0.5 with 2+ set appearances should label 'battle-tested'."""
    t = _make_track(play_count=5, kiku_play_count=2, rating=4)
    score, label = track_quality(t, discovery_density=0.5, set_appearance_count=3)
    assert label == "battle-tested"


def test_track_quality_density_crowd_favorite():
    """discovery_density=+0.5 with 7+ plays should label 'crowd favorite'."""
    t = _make_track(play_count=5, kiku_play_count=3, rating=4)
    score, label = track_quality(t, discovery_density=0.5, set_appearance_count=0)
    assert label == "crowd favorite"


def test_track_quality_discovery_boosts_unplayed():
    """Unplayed track should score higher with discovery bias than neutral."""
    t = _make_track(play_count=0, kiku_play_count=0, rating=3)
    score_neutral, _ = track_quality(t, discovery_density=0.0)
    score_discovery, _ = track_quality(t, discovery_density=-1.0)
    assert score_discovery > score_neutral


def test_track_quality_density_boosts_popular():
    """Highly-played track should score higher with density bias."""
    t = _make_track(play_count=10, kiku_play_count=0, rating=3)
    score_neutral, _ = track_quality(t, discovery_density=0.0)
    score_density, _ = track_quality(t, discovery_density=1.0, set_appearance_count=5)
    assert score_density > score_neutral
