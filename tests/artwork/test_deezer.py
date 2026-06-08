"""Tests for the Deezer cover source (mock transport + throttle reset)."""

from __future__ import annotations

import httpx
import pytest

from kiku.artwork.deezer import DeezerClient


@pytest.fixture(autouse=True)
def _reset_throttle():
    DeezerClient._last_request_at = 0.0
    yield
    DeezerClient._last_request_at = 0.0


IMG = b"\xff\xd8\xff\xe0deezer-jpeg"


def _handler(data, captured=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if "api.deezer.com" in request.url.host:
            if captured is not None:
                captured["search_url"] = str(request.url)
            return httpx.Response(200, json={"data": data})
        if captured is not None:
            captured["img_url"] = str(request.url)
        return httpx.Response(200, content=IMG, headers={"content-type": "image/jpeg"})

    return handler


def test_search_cover_prefers_cover_xl_and_matches_nested_artist():
    captured: dict = {}
    data = [
        {"title": "Bite The Hand That Feeds You", "artist": {"name": "Hadone"},
         "cover_big": "https://e-cdn/cover/big.jpg",
         "cover_xl": "https://e-cdn/cover/xl.jpg"},
    ]
    client = DeezerClient(transport=httpx.MockTransport(_handler(data, captured)))
    out = client.search_cover("Hadone", "Bite The Hand That Feeds You")
    assert out is not None
    content, ct = out
    assert content == IMG
    assert captured["img_url"].endswith("xl.jpg")  # cover_xl preferred over cover_big


def test_search_cover_falls_back_to_cover_big_then_cover():
    data = [
        {"title": "Bite The Hand That Feeds You", "artist": {"name": "Hadone"},
         "cover": "https://e-cdn/cover/small.jpg"},
    ]
    captured: dict = {}
    client = DeezerClient(transport=httpx.MockTransport(_handler(data, captured)))
    assert client.search_cover("Hadone", "Bite The Hand That Feeds You") is not None
    assert captured["img_url"].endswith("small.jpg")


def test_search_cover_rejects_below_threshold():
    data = [
        {"title": "Completely Unrelated", "artist": {"name": "Nobody"},
         "cover_xl": "https://e-cdn/cover/xl.jpg"},
    ]
    client = DeezerClient(transport=httpx.MockTransport(_handler(data)))
    assert client.search_cover("Hadone", "Bite The Hand That Feeds You") is None


def test_search_network_error_soft_fails():
    def boom(request):
        raise httpx.ConnectError("offline")

    client = DeezerClient(transport=httpx.MockTransport(boom))
    assert client.search_cover("Hadone", "Bite The Hand That Feeds You") is None
