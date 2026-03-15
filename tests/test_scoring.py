"""Tests for transition scoring."""

from kiku.setbuilder.scoring import bpm_compatibility, genre_coherence


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
