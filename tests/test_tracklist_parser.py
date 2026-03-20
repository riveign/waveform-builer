"""Unit tests for tracklist parsers."""

from __future__ import annotations

from kiku.hunting.parsers.common import normalize_name, parse_artist_title, parse_remix
from kiku.hunting.parsers.tracklist import (
    merge_tracklists,
    parse_chapters,
    parse_comments,
    parse_description,
)


# ── common.py tests ──


def test_parse_artist_title_basic():
    assert parse_artist_title("Bicep - Glue") == ("Bicep", "Glue")


def test_parse_artist_title_em_dash():
    assert parse_artist_title("Four Tet — Baby") == ("Four Tet", "Baby")


def test_parse_artist_title_en_dash():
    assert parse_artist_title("Aphex Twin – Xtal") == ("Aphex Twin", "Xtal")


def test_parse_artist_title_no_separator():
    assert parse_artist_title("Just a track name") is None


def test_parse_remix():
    title, remix = parse_remix("Glue (Hammer Remix)")
    assert title == "Glue"
    assert remix == "Hammer Remix"


def test_parse_remix_no_remix():
    title, remix = parse_remix("Original Track")
    assert title == "Original Track"
    assert remix is None


def test_parse_remix_edit():
    title, remix = parse_remix("Track Name [DJ Edit]")
    assert title == "Track Name"
    assert remix == "DJ Edit"


def test_normalize_name():
    assert normalize_name("  BICEP  ") == "bicep"
    assert normalize_name("Artist feat. Singer") == "artist"
    assert normalize_name("Artist ft. Other") == "artist"


# ── tracklist.py tests ──


def test_parse_description_numbered():
    text = """Tracklist:
1. Bicep - Glue
2. Four Tet - Baby
3. Hammer - Catnip (Original Mix)
"""
    tracks = parse_description(text)
    assert len(tracks) == 3
    assert tracks[0].artist == "Bicep"
    assert tracks[0].title == "Glue"
    assert tracks[2].remix_info == "Original Mix"


def test_parse_description_timestamped():
    text = """00:00 Intro
03:15 Bicep - Glue
08:30 Four Tet - Baby
"""
    tracks = parse_description(text)
    assert len(tracks) >= 2
    bicep = next(t for t in tracks if t.artist == "Bicep")
    assert bicep.timestamp_sec == 195.0  # 3*60 + 15


def test_parse_description_empty():
    assert parse_description(None) == []
    assert parse_description("") == []


def test_parse_chapters():
    chapters = [
        {"title": "Bicep - Glue", "start_time": 0, "end_time": 300},
        {"title": "Four Tet - Baby", "start_time": 300, "end_time": 600},
    ]
    tracks = parse_chapters(chapters)
    assert len(tracks) == 2
    assert tracks[0].source == "chapter"
    assert tracks[0].confidence == 0.95


def test_parse_comments_timestamped():
    comments = [
        {"text": "32:15 Bicep - Glue", "timestamp": None, "author": "fan1"},
        {"text": "love this set!", "timestamp": None, "author": "fan2"},
    ]
    tracks = parse_comments(comments)
    assert len(tracks) == 1
    assert tracks[0].artist == "Bicep"
    assert tracks[0].timestamp_sec == 32 * 60 + 15


def test_merge_tracklists_dedup():
    from kiku.hunting.parsers.tracklist import ParsedTrack

    list_a = [ParsedTrack(position=1, artist="Bicep", title="Glue", confidence=0.9)]
    list_b = [ParsedTrack(position=1, artist="bicep", title="glue", confidence=0.6)]
    merged = merge_tracklists(list_a, list_b)
    assert len(merged) == 1
    assert merged[0].confidence == 0.9  # Higher confidence wins
