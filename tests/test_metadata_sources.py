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
        "Bite The Hand That Feeds You",
        "Leave The Door Open",
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
        {
            "position": "A1",
            "type_": "track",
            "title": "Bite The Hand That Feeds You",
            "duration": "4:49",
        },
        {"position": "", "type_": "heading", "title": "Side B"},
        {"position": "B1", "type_": "track", "title": "Sit In Their Seat", "duration": "5:18"},
    ],
}


def test_discogs_unavailable_without_token(monkeypatch):
    """`token=None` means "use whatever is configured" — so isolate the config.

    Without this the test passes only on a machine that has never configured a
    Discogs token, and starts failing the day the DJ adds one.
    """
    monkeypatch.delenv("KIKU_DISCOGS_TOKEN", raising=False)
    monkeypatch.setattr("kiku.metadata.sources.discogs.get_discogs_token", lambda: None)
    assert DiscogsSource(token=None).available() is False


def test_discogs_fetch_release_reads_the_side_off_the_pressing():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=DISCOGS_RELEASE)

    src = DiscogsSource(token="fake", transport=httpx.MockTransport(handler))
    cand = src.fetch_url("https://www.discogs.com/release/12345-x")
    assert cand is not None
    assert cand.album == "Bite The Hand That Feeds You"
    assert cand.label == "Primal Instinct"
    assert cand.year == 2026
    # Heading dropped. A1/B1 are real side positions, not a sequence to flatten
    # (spec 030): the side becomes disc, the index within it becomes position,
    # and the raw string is kept because it is what is printed on the label.
    assert [(r.disc, r.position, r.position_raw, r.title) for r in cand.recordings] == [
        (1, 1, "A1", "Bite The Hand That Feeds You"),
        (2, 1, "B1", "Sit In Their Seat"),
    ]
    assert cand.recordings[0].length_ms == 289000


def test_discogs_falls_back_to_free_text_when_the_title_is_a_track_name():
    """A DJ names a record by the track on it. The structured search returns 0.

    Measured against the live API: `release_title=AF 97&artist=Alarico` finds
    nothing; free-text finds Klockworks 38, whose A1 it is.
    """
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        if request.url.path == "/database/search":
            seen.append(params)
            if "release_title" in params:
                return httpx.Response(200, json={"results": []})
            return httpx.Response(200, json={"results": [{"id": 12345}]})
        return httpx.Response(200, json=DISCOGS_RELEASE)

    src = DiscogsSource(token="fake", transport=httpx.MockTransport(handler))
    cands = src.search("AF 97", "Alarico", limit=3)

    assert [p.get("release_title") or p.get("q") for p in seen] == ["AF 97", "Alarico AF 97"]
    assert len(cands) == 1


def test_discogs_search_does_not_fall_back_when_it_already_found_something():
    """The fallback is a rescue, not a second opinion — it must not fire."""
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/database/search":
            calls.append(dict(request.url.params))
            return httpx.Response(200, json={"results": [{"id": 12345}]})
        return httpx.Response(200, json=DISCOGS_RELEASE)

    src = DiscogsSource(token="fake", transport=httpx.MockTransport(handler))
    src.search("Bite The Hand That Feeds You", "Hadone", limit=3)

    assert len(calls) == 1
    assert "release_title" in calls[0]


def test_discogs_carries_the_catalog_facts_a_pressing_is_made_of():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                **DISCOGS_RELEASE,
                "country": "Germany",
                "labels": [{"name": "Klockworks", "catno": "KW 38"}],
                "formats": [{"name": "Vinyl", "descriptions": ['12"', "33 1/3 RPM", "EP"]}],
                "images": [{"uri": "https://i.discogs.com/x.jpg"}],
            },
        )

    src = DiscogsSource(token="fake", transport=httpx.MockTransport(handler))
    cand = src.fetch_url("https://www.discogs.com/release/12345-x")
    assert cand is not None
    assert cand.catalog_number == "KW 38"
    assert cand.country == "Germany"
    assert cand.format == 'Vinyl, 12", 33 1/3 RPM, EP'
    assert cand.cover_url == "https://i.discogs.com/x.jpg"


def test_rpm_is_none_when_the_pressing_does_not_say():
    """Three of four sampled 12"s carried no RPM description. NULL, not a guess."""
    from kiku.metadata.sources.discogs import rpm_from_format

    assert rpm_from_format('Vinyl, 12", 33 1/3 RPM, EP') == 33
    assert rpm_from_format('Vinyl, 7", 45 RPM') == 45
    assert rpm_from_format('Vinyl, 12"') is None
    assert rpm_from_format(None) is None


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
            "media": [
                {
                    "position": 1,
                    "tracks": [
                        {"position": 1, "title": "Track One", "length": 200000},
                        {"position": 2, "title": "Track Two"},
                    ],
                }
            ],
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
