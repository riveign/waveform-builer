"""Tests for the Cover Art Archive fetcher (CAA)."""

from __future__ import annotations

import httpx
import pytest

from kiku.musicbrainz import cover_art


@pytest.fixture(autouse=True)
def _tmp_data_dir(tmp_path, monkeypatch):
    """Redirect KIKU_DATA_DIR so cover_art tests don't write into the real data/."""
    monkeypatch.setenv("KIKU_DATA_DIR", str(tmp_path))
    yield


def test_fetch_front_cover_caches_image(tmp_path) -> None:
    payload = b"\xff\xd8\xff\xe0fake-jpeg"

    def handler(request: httpx.Request) -> httpx.Response:
        assert "release/mb-rel-1/front" in str(request.url)
        return httpx.Response(
            200,
            content=payload,
            headers={"content-type": "image/jpeg"},
        )

    path = cover_art.fetch_front_cover(
        "mb-rel-1", "abcd1234abcd", transport=httpx.MockTransport(handler)
    )
    assert path is not None
    assert path.suffix == ".jpg"
    assert path.read_bytes() == payload

    # Second call should hit the cache (no transport needed)
    again = cover_art.fetch_front_cover("mb-rel-1", "abcd1234abcd")
    assert again == path


def test_fetch_front_cover_404_marks_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    path = cover_art.fetch_front_cover(
        "mb-missing", "ffff0000ffff", transport=httpx.MockTransport(handler)
    )
    assert path is None
    assert cover_art.is_cover_known_missing("ffff0000ffff")

    # Subsequent calls must not hit the network — pass a handler that would fail
    def boom(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not be called after missing-mark")

    second = cover_art.fetch_front_cover(
        "mb-missing", "ffff0000ffff", transport=httpx.MockTransport(boom)
    )
    assert second is None


def test_fetch_front_cover_png_extension() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"\x89PNGfake", headers={"content-type": "image/png"}
        )

    path = cover_art.fetch_front_cover(
        "mb-png", "pngpngpngpng", transport=httpx.MockTransport(handler)
    )
    assert path is not None
    assert path.suffix == ".png"


def test_fetch_front_cover_oversize_rejected() -> None:
    huge = b"x" * (cover_art.MAX_BYTES + 1)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=huge, headers={"content-type": "image/jpeg"}
        )

    path = cover_art.fetch_front_cover(
        "mb-huge", "hugeghugeghu", transport=httpx.MockTransport(handler)
    )
    assert path is None


def test_fetch_front_cover_empty_id() -> None:
    """Empty mb_release_id → don't even attempt."""
    assert cover_art.fetch_front_cover("", "anyany00anyy") is None
