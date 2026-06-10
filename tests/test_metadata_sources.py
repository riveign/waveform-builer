"""Parser tests for each metadata source against captured fixtures (no network)."""

from __future__ import annotations

import httpx
import pytest

from kiku.metadata.sources import available_sources, get_source
from kiku.metadata.sources.bandcamp import BandcampSource, parse_bandcamp_html
from kiku.metadata.sources.discogs import DiscogsSource, _duration_to_ms, _join_artists
from kiku.metadata.sources.musicbrainz import MusicBrainzSource
from kiku.metadata.sources.tags import _parse_int, _parse_year

# ── Bandcamp ────────────────────────────────────────────────────────────

BANDCAMP_HTML = """
<html><head>
<script type="application/ld+json">
{"@type":"MusicAlbum","name":"Bite The Hand That Feeds You",
 "byArtist":{"name":"Hadone"},"datePublished":"15 May 2026 00:00:00 GMT",
 "publisher":{"name":"Primal Instinct"}}
</script>
</head><body>
<script type="text/javascript" data-tralbum='{"artist":"Hadone",
 "current":{"title":"Bite The Hand That Feeds You"},
 "trackinfo":[{"title":"Bite The Hand That Feeds You","track_num":1,"duration":289.4},
              {"title":"Leave The Door Open","track_num":2,"duration":282.0}]}'></script>
</body></html>
"""


def test_bandcamp_parses_tralbum_and_ld():
    cand = parse_bandcamp_html(BANDCAMP_HTML, "https://x.bandcamp.com/album/y")
    assert cand is not None
    assert cand.source == "bandcamp"
    assert cand.album == "Bite The Hand That Feeds You"
    assert cand.artist == "Hadone"
    assert cand.label == "Primal Instinct"
    assert cand.year == 2026
    assert [r.title for r in cand.recordings] == [
        "Bite The Hand That Feeds You", "Leave The Door Open",
    ]
    assert cand.recordings[0].position == 1
    assert cand.recordings[0].length_ms == 289400


def test_bandcamp_fetch_url_via_mock_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=BANDCAMP_HTML)

    src = BandcampSource(transport=httpx.MockTransport(handler))
    cand = src.fetch_url("https://x.bandcamp.com/album/y")
    assert cand is not None and cand.track_count == 2


def test_bandcamp_returns_none_on_junk():
    assert parse_bandcamp_html("<html></html>", "u") is None


# ── Discogs ─────────────────────────────────────────────────────────────

DISCOGS_RELEASE = {
    "title": "Bite The Hand That Feeds You",
    "artists": [{"name": "Hadone"}],
    "year": 2026,
    "labels": [{"name": "Primal Instinct"}],
    "tracklist": [
        {"position": "A1", "type_": "track", "title": "Bite The Hand That Feeds You", "duration": "4:49"},
        {"position": "", "type_": "heading", "title": "Side B"},
        {"position": "B1", "type_": "track", "title": "Sit In Their Seat", "duration": "5:18"},
    ],
}


def test_discogs_unavailable_without_token():
    assert DiscogsSource(token=None).available() is False


def test_discogs_fetch_release_skips_headings_and_sequences_positions():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=DISCOGS_RELEASE)

    src = DiscogsSource(token="fake", transport=httpx.MockTransport(handler))
    cand = src.fetch_url("https://www.discogs.com/release/12345-x")
    assert cand is not None
    assert cand.album == "Bite The Hand That Feeds You"
    assert cand.label == "Primal Instinct"
    assert cand.year == 2026
    # Heading dropped; positions resequenced 1..2 regardless of A1/B1.
    assert [(r.position, r.title) for r in cand.recordings] == [
        (1, "Bite The Hand That Feeds You"), (2, "Sit In Their Seat"),
    ]
    assert cand.recordings[0].length_ms == 289000


def test_discogs_join_artists_strips_dupe_suffix():
    assert _join_artists([{"name": "Hadone (2)"}]) == "Hadone"
    assert _join_artists([{"name": "A", "join": "&"}, {"name": "B"}]) == "A & B"


def test_duration_to_ms():
    assert _duration_to_ms("4:49") == 289000
    assert _duration_to_ms("") is None
    assert _duration_to_ms("bogus") is None


# ── MusicBrainz (wrapper over existing client) ───────────────────────────

class _FakeMBClient:
    def search_releases(self, album, artist, limit=3):
        return [{"id": "rel-1", "score": 100}]

    def get_release(self, mb_id):
        return {
            "id": mb_id,
            "title": "Some EP",
            "artist-credit": [{"name": "Hadone"}],
            "date": "2026-05-15",
            "label-info": [{"label": {"name": "Primal Instinct"}}],
            "media": [{"position": 1, "tracks": [
                {"position": 1, "title": "Track One", "length": 200000},
                {"position": 2, "title": "Track Two"},
            ]}],
        }


def test_musicbrainz_source_maps_release():
    src = MusicBrainzSource(client=_FakeMBClient())
    cands = src.search("Some EP", "Hadone")
    assert len(cands) == 1
    c = cands[0]
    assert c.source == "musicbrainz"
    assert c.artist == "Hadone"
    assert c.label == "Primal Instinct"
    assert c.year == 2026
    assert [(r.position, r.title) for r in c.recordings] == [(1, "Track One"), (2, "Track Two")]


# ── Tags helpers ─────────────────────────────────────────────────────────

def test_parse_int_handles_slash_and_side_prefix():
    assert _parse_int("3/8") == 3
    assert _parse_int("A1") == 1
    assert _parse_int(None) is None
    assert _parse_int("none") is None


def test_parse_year():
    assert _parse_year("2026-05-15") == 2026
    assert _parse_year("15 May 2026") == 2026
    assert _parse_year(None) is None


# ── Registry ─────────────────────────────────────────────────────────────

def test_available_sources_shape():
    rows = {r["name"]: r for r in available_sources()}
    assert set(rows) == {"bandcamp", "musicbrainz", "discogs", "tags"}
    assert rows["bandcamp"]["lookup_mode"] == "url"
    assert rows["musicbrainz"]["lookup_mode"] == "search"


def test_get_source_unknown_raises():
    with pytest.raises(ValueError):
        get_source("lastfm")
