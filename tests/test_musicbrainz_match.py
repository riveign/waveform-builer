"""Tests for normalize_title + match_tracklist."""

from __future__ import annotations

from kiku.musicbrainz.match import match_tracklist, normalize_title


def test_normalize_title_strips_paren_variants() -> None:
    assert normalize_title("Track Name (Original Mix)") == "track name"
    assert normalize_title("Track Name (Extended Mix)") == "track name"
    assert normalize_title("Track Name (Radio Edit)") == "track name"


def test_normalize_title_strips_feat() -> None:
    assert normalize_title("Hey Joe feat. Someone") == "hey joe"
    assert normalize_title("Hey Joe ft. Someone Else") == "hey joe"
    assert normalize_title("Hey Joe featuring The Band") == "hey joe"


def test_normalize_title_strips_remix_suffix() -> None:
    assert normalize_title("Track (Joe's Remix)") == "track"
    assert normalize_title("Track [Some Guy Remix]") == "track"


def test_normalize_title_empty() -> None:
    assert normalize_title("") == ""
    assert normalize_title(None) == ""


def test_normalize_title_lowercases_and_collapses_whitespace() -> None:
    assert normalize_title("  HELLO    World  ") == "hello world"


def test_match_tracklist_perfect_match() -> None:
    kiku = [
        {"id": 10, "title": "Intro"},
        {"id": 11, "title": "Main Theme"},
        {"id": 12, "title": "Outro"},
    ]
    mb = [
        {"position": 1, "disc": 1, "title": "Intro"},
        {"position": 2, "disc": 1, "title": "Main Theme"},
        {"position": 3, "disc": 1, "title": "Outro"},
    ]
    result = match_tracklist(kiku, mb)
    assert [r["mb_position"] for r in result] == [1, 2, 3]
    assert all(r["confidence"] == 1.0 for r in result)
    assert [r["track_id"] for r in result] == [10, 11, 12]


def test_match_tracklist_handles_remix_suffix() -> None:
    """A 'Track (Original Mix)' on Kiku should match plain 'Track' on MB."""
    kiku = [{"id": 1, "title": "Sunset (Original Mix)"}]
    mb = [{"position": 5, "disc": 1, "title": "Sunset"}]
    result = match_tracklist(kiku, mb)
    assert result[0]["mb_position"] == 5
    assert result[0]["confidence"] >= 0.95


def test_match_tracklist_unmatched_track() -> None:
    """A Kiku track with no close MB candidate is left with mb_position=None."""
    kiku = [
        {"id": 1, "title": "Alpha"},
        {"id": 2, "title": "Beta"},
    ]
    mb = [{"position": 1, "disc": 1, "title": "Alpha"}]
    result = match_tracklist(kiku, mb)
    # First kiku gets MB
    by_id = {r["track_id"]: r for r in result}
    assert by_id[1]["mb_position"] == 1
    # Second has no remaining MB slot
    assert by_id[2]["mb_position"] is None
    assert by_id[2]["confidence"] == 0.0


def test_match_tracklist_greedy_picks_best_first() -> None:
    """Best global score wins, even if order differs."""
    kiku = [
        {"id": 1, "title": "Far Apart Title"},
        {"id": 2, "title": "Exact Match"},
    ]
    mb = [
        {"position": 1, "disc": 1, "title": "Exact Match"},
        {"position": 2, "disc": 1, "title": "Totally Different Words"},
    ]
    result = match_tracklist(kiku, mb)
    by_id = {r["track_id"]: r for r in result}
    # The exact match should be assigned to track 2
    assert by_id[2]["mb_position"] == 1
    assert by_id[2]["confidence"] == 1.0


def test_match_tracklist_preserves_disc_number() -> None:
    kiku = [{"id": 1, "title": "Side B Opener"}]
    mb = [{"position": 1, "disc": 2, "title": "Side B Opener"}]
    result = match_tracklist(kiku, mb)
    assert result[0]["mb_disc"] == 2
