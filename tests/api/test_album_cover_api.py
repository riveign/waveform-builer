"""Integration tests for cover resolution at the API layer (offline, mocked sources)."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.api.deps import get_db
from kiku.api.main import create_app
from kiku.db.models import AlbumMetadata, Base, Track
from kiku.metadata.album_key import album_key

IMG = b"\xff\xd8\xff\xe0album-cover"


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'c.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    # Track 1: file absent → no embedded art, must inherit album cover.
    s.add(Track(id=1, title="Moonrise", artist="Luna", album="Night EP",
                file_path="/nope/Luna/Night EP/01.flac", track_number=1))
    # Track 2: a real but corrupt file → embedded extraction must soft-fail.
    bad = tmp_path / "broken.mp3"
    bad.write_bytes(b"not an mp3 at all")
    s.add(Track(id=2, title="Eclipse", artist="Luna", album="Night EP",
                file_path=str(bad), track_number=2))
    s.commit()
    yield s
    s.close()


@pytest.fixture()
def client(db, tmp_path, monkeypatch):
    monkeypatch.setenv("KIKU_DATA_DIR", str(tmp_path / "cache"))
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _itunes_hit(self, artist, album):
    return (IMG, "image/jpeg")


def _miss(self, artist, album):
    return None


def test_track_inherits_album_cover_via_itunes(client, monkeypatch):
    monkeypatch.setattr("kiku.artwork.itunes.ItunesClient.search_cover", _itunes_hit)
    monkeypatch.setattr("kiku.artwork.deezer.DeezerClient.search_cover", _miss)

    res = client.get("/api/tracks/1/artwork")
    assert res.status_code == 200
    assert res.content == IMG


def test_track_artwork_never_500_on_corrupt_file(client, monkeypatch):
    # Embedded extraction soft-fails; external sources miss → clean 404, never 500.
    monkeypatch.setattr("kiku.artwork.itunes.ItunesClient.search_cover", _miss)
    monkeypatch.setattr("kiku.artwork.deezer.DeezerClient.search_cover", _miss)

    res = client.get("/api/tracks/2/artwork")
    assert res.status_code == 404  # the key assertion: NOT 500


def test_album_cover_resolves_and_records_source(client, db, monkeypatch):
    monkeypatch.setattr("kiku.artwork.itunes.ItunesClient.search_cover", _itunes_hit)
    monkeypatch.setattr("kiku.artwork.deezer.DeezerClient.search_cover", _miss)

    key = album_key("Night EP", "Luna")
    res = client.get(f"/api/albums/{key}/cover")
    assert res.status_code == 200
    assert res.content == IMG

    md = db.get(AlbumMetadata, key)
    assert md is not None and md.cover_source == "itunes"

    # Album-tracks DTO surfaces the source for UI attribution.
    detail = client.get(f"/api/albums/{key}/tracks").json()
    assert detail["album"]["cover_source"] == "itunes"
