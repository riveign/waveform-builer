"""Unit tests for the artist-token matcher."""

from __future__ import annotations

from kiku.artists import artist_matches, artist_tokens


def test_tokens_basic():
    assert artist_tokens("Bicep & Chroma") == {"bicep", "chroma"}
    assert artist_tokens("X feat. Bicep") == {"x", "bicep"}
    assert artist_tokens("Bicep, Other") == {"bicep", "other"}
    assert artist_tokens("A vs B") == {"a", "b"}
    assert artist_tokens("A with B") == {"a", "b"}
    assert artist_tokens("A ft. B") == {"a", "b"}
    assert artist_tokens("A + B") == {"a", "b"}


def test_tokens_word_boundary():
    # "x"/"with"/"vs" only split as whole words, not substrings.
    assert artist_tokens("Maxx") == {"maxx"}
    assert artist_tokens("Sixx") == {"sixx"}


def test_tokens_case_whitespace():
    assert artist_tokens("  BICEP  &  chroma ") == {"bicep", "chroma"}


def test_tokens_empty_none():
    assert artist_tokens(None) == set()
    assert artist_tokens("") == set()
    assert artist_tokens("   ") == set()


def test_matches_collaborations():
    assert artist_matches("Bicep", "Bicep & Chroma")
    assert artist_matches("Bicep", "X feat. Bicep")
    assert artist_matches("Bicep", "Bicep, Other")
    assert artist_matches("Chroma", "Bicep & Chroma")


def test_matches_near_miss():
    assert not artist_matches("Bicep", "Bicepz")
    assert not artist_matches("Maxx", "Max")
    assert not artist_matches("Bicep", "Other Artist")


def test_matches_case_whitespace():
    assert artist_matches("  bicep ", "Bicep & Chroma")


def test_matches_empty_none():
    assert not artist_matches(None, "Bicep")
    assert not artist_matches("", "Bicep")
    assert not artist_matches("Bicep", None)
    assert not artist_matches("Bicep", "")
