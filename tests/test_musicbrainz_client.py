"""Tests for the MusicBrainz HTTP client (mock transport + throttle)."""

from __future__ import annotations

import time

import httpx
import pytest

from kiku.musicbrainz import client as mb_client_mod
from kiku.musicbrainz.client import MusicBrainzClient


@pytest.fixture(autouse=True)
def _reset_throttle() -> None:
    """Reset the class-level throttle gate between tests so they don't interact."""
    MusicBrainzClient._last_request_at = 0.0
    yield
    MusicBrainzClient._last_request_at = 0.0


def _make_transport(handler):
    return httpx.MockTransport(handler)


def test_search_releases_sends_query_and_user_agent() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["ua"] = request.headers.get("User-Agent")
        return httpx.Response(
            200,
            json={
                "releases": [
                    {"id": "abc", "title": "Foo", "score": 100},
                ]
            },
        )

    with MusicBrainzClient(transport=_make_transport(handler)) as c:
        releases = c.search_releases("Foo Album", "Bar Artist", limit=2)

    assert releases == [{"id": "abc", "title": "Foo", "score": 100}]
    assert "release/" in captured["url"]
    assert "Foo+Album" in captured["url"] or "Foo%20Album" in captured["url"]
    assert "Bar+Artist" in captured["url"] or "Bar%20Artist" in captured["url"]
    # User-Agent must be set per MB etiquette
    assert captured["ua"] and "Kiku" in captured["ua"]


def test_get_release_inc_recordings() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"id": "rel-1", "title": "Release", "media": []},
        )

    with MusicBrainzClient(transport=_make_transport(handler)) as c:
        data = c.get_release("rel-1")

    assert data["id"] == "rel-1"
    assert "recordings" in captured["url"]


def test_throttle_enforces_1s_between_requests(monkeypatch) -> None:
    """Two back-to-back requests should sleep ~1s on the second one."""
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(mb_client_mod.time, "sleep", fake_sleep)

    # Monotonic stub: simulate ~0s elapsed between the two requests
    fake_now = [100.0]

    def fake_monotonic() -> float:
        return fake_now[0]

    monkeypatch.setattr(mb_client_mod.time, "monotonic", fake_monotonic)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"releases": []})

    with MusicBrainzClient(transport=_make_transport(handler)) as c:
        c.search_releases("A", "B")
        c.search_releases("A", "B")

    # First call: no prior request → no sleep (or near-zero)
    # Second call: should require ~MIN_REQUEST_INTERVAL_S sleep
    assert any(s >= 0.99 for s in sleeps), f"expected ~1s sleep, got {sleeps}"


def test_http_error_propagates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    with MusicBrainzClient(transport=_make_transport(handler)) as c:
        with pytest.raises(httpx.HTTPStatusError):
            c.search_releases("A", "B")
