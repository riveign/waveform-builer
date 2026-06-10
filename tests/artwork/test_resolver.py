"""Tests for the cover resolution chain, embedded soft-fail, and .missing TTL."""

from __future__ import annotations

import time

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.artwork.deezer import DeezerClient
from kiku.artwork.itunes import ItunesClient
from kiku.artwork.resolver import embedded_cover_bytes, resolve_album_cover
from kiku.db.models import AlbumMetadata, Base, Track
from kiku.metadata.album_key import album_key

IMG = b"\xff\xd8\xff\xe0cover-bytes"


@pytest.fixture(autouse=True)
def _reset_throttle():
    ItunesClient._last_request_at = 0.0
    DeezerClient._last_request_at = 0.0
    yield


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KIKU_DATA_DIR", str(tmp_path))
    yield tmp_path


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'a.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    # Album with file paths that don't exist → embedded always soft-fails to None.
    for i in range(1, 3):
        s.add(Track(id=i, title=f"Solar {i}", artist="Astral", album="Solar EP",
                    file_path=f"/nope/Astral/Solar EP/0{i}.flac", track_number=i))
    s.commit()
    yield s
    s.close()


def _transport(*, itunes=None, deezer=None, caa_status=404):
    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if "itunes.apple.com" in host:
            return httpx.Response(200, json={"results": itunes or []})
        if "api.deezer.com" in host:
            return httpx.Response(200, json={"data": deezer or []})
        if "coverartarchive.org" in host:
            if caa_status != 200:
                return httpx.Response(caa_status)
            return httpx.Response(200, content=IMG, headers={"content-type": "image/jpeg"})
        # image CDN download
        return httpx.Response(200, content=IMG, headers={"content-type": "image/jpeg"})

    return httpx.MockTransport(handler)


KEY = album_key("Solar EP", "Astral")


def test_resolves_via_itunes_and_records_source(session):
    itunes = [{"collectionType": "Album", "artistName": "Astral",
               "collectionName": "Solar EP",
               "artworkUrl100": "https://is1.mzstatic.com/100x100bb.jpg"}]
    result = resolve_album_cover(session, KEY, transport=_transport(itunes=itunes))
    assert result is not None
    path, source = result
    assert source == "itunes"
    assert path.read_bytes() == IMG
    md = session.get(AlbumMetadata, KEY)
    assert md.cover_source == "itunes" and md.cover_fetched_at is not None


def test_falls_through_itunes_to_deezer(session):
    deezer = [{"title": "Solar EP", "artist": {"name": "Astral"},
               "cover_xl": "https://e-cdn/xl.jpg"}]
    result = resolve_album_cover(session, KEY, transport=_transport(itunes=[], deezer=deezer))
    assert result is not None and result[1] == "deezer"


def test_caa_used_when_mb_release_known_before_external(session):
    session.add(AlbumMetadata(album_key=KEY, album="Solar EP", album_artist="Astral",
                              mb_release_id="rel-1"))
    session.commit()
    # iTunes/Deezer return nothing; CAA returns an image → CAA wins.
    result = resolve_album_cover(session, KEY, transport=_transport(caa_status=200))
    assert result is not None and result[1] == "caa"


def test_all_miss_writes_missing_sentinel_and_returns_none(session, _data_dir):
    result = resolve_album_cover(session, KEY, transport=_transport())
    assert result is None
    assert (_data_dir / "cover_art" / f"{KEY}.missing").exists()


def test_cache_hit_short_circuits_without_network(session, _data_dir):
    cover_dir = _data_dir / "cover_art"
    cover_dir.mkdir(parents=True)
    (cover_dir / f"{KEY}.jpg").write_bytes(IMG)

    def boom(request):
        raise AssertionError("network must not be touched on a cache hit")

    result = resolve_album_cover(session, KEY, transport=httpx.MockTransport(boom))
    assert result is not None and result[0].read_bytes() == IMG


def test_embedded_soft_fails_on_unreadable_file(tmp_path):
    bad = tmp_path / "broken.mp3"
    bad.write_bytes(b"not really an mp3")
    assert embedded_cover_bytes(str(bad)) is None
    assert embedded_cover_bytes(str(tmp_path / "missing.flac")) is None


def test_missing_sentinel_ttl_boundary(_data_dir):
    from kiku.musicbrainz.cover_art import is_cover_known_missing, mark_cover_missing

    mark_cover_missing("k1")
    assert is_cover_known_missing("k1") is True  # fresh → still missing

    sentinel = _data_dir / "cover_art" / "k1.missing"
    old = time.time() - 31 * 86400
    import os
    os.utime(sentinel, (old, old))
    assert is_cover_known_missing("k1", ttl_days=30) is False  # stale → retry
    assert not sentinel.exists()  # stale sentinel cleared
