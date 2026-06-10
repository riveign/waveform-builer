"""Tests for the iTunes cover source (mock transport + throttle reset)."""

from __future__ import annotations

import httpx
import pytest

from kiku.artwork.itunes import ItunesClient, _upscale


@pytest.fixture(autouse=True)
def _reset_throttle():
    ItunesClient._last_request_at = 0.0
    yield
    ItunesClient._last_request_at = 0.0


IMG = b"\xff\xd8\xff\xe0itunes-jpeg"


def _handler(results, captured=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if "itunes.apple.com" in request.url.host:
            if captured is not None:
                captured["search_url"] = str(request.url)
            return httpx.Response(200, json={"resultCount": len(results), "results": results})
        # image CDN
        if captured is not None:
            captured["img_url"] = str(request.url)
        return httpx.Response(200, content=IMG, headers={"content-type": "image/jpeg"})

    return handler


def test_search_cover_picks_match_and_upscales():
    captured: dict = {}
    results = [
        {"collectionType": "Album", "artistName": "Hadone",
         "collectionName": "Bite The Hand That Feeds You",
         "artworkUrl100": "https://is1.mzstatic.com/image/.../100x100bb.jpg"},
    ]
    client = ItunesClient(transport=httpx.MockTransport(_handler(results, captured)))
    out = client.search_cover("Hadone", "Bite The Hand That Feeds You")
    assert out is not None
    content, ct = out
    assert content == IMG and ct.startswith("image/jpeg")
    # upscaled the artwork URL before downloading
    assert "600x600bb.jpg" in captured["img_url"]
    assert "entity=album" in captured["search_url"]


def test_search_cover_rejects_wrong_artist():
    results = [
        {"collectionType": "Album", "artistName": "Someone Else",
         "collectionName": "A Totally Different Record",
         "artworkUrl100": "https://x/100x100bb.jpg"},
    ]
    client = ItunesClient(transport=httpx.MockTransport(_handler(results)))
    assert client.search_cover("Hadone", "Bite The Hand That Feeds You") is None


def test_search_cover_various_artists_matches_album_only():
    results = [
        {"collectionType": "Album", "artistName": "VA / Compilation Crew",
         "collectionName": "Summer Sampler 2026",
         "artworkUrl100": "https://x/100x100bb.jpg"},
    ]
    client = ItunesClient(transport=httpx.MockTransport(_handler(results)))
    # Album title matches; artist is "Various Artists" so artist mismatch is ignored.
    assert client.search_cover("Various Artists", "Summer Sampler 2026") is not None


def test_search_cover_empty_album_returns_none():
    client = ItunesClient(transport=httpx.MockTransport(_handler([])))
    assert client.search_cover("Hadone", "") is None


def test_search_network_error_soft_fails():
    def boom(request):
        raise httpx.ConnectError("offline")

    client = ItunesClient(transport=httpx.MockTransport(boom))
    assert client.search_cover("Hadone", "Bite The Hand That Feeds You") is None


def test_upscale_helper():
    assert _upscale("https://x/100x100bb.jpg") == "https://x/600x600bb.jpg"
