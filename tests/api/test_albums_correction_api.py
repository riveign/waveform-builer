"""Integration tests for the multi-source correction endpoints (spec 016)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.api.deps import get_db
from kiku.api.main import create_app
from kiku.db.models import AlbumMetadata, Base, Track
from kiku.metadata.album_key import album_key
from kiku.metadata.models import RecordingCandidate, ReleaseCandidate


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'a.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    for i in range(1, 4):
        session.add(Track(
            id=i, title=f"Mangled {i}", artist="A%d hadone" % i,
            album="Solar EP", release_year=2020, label="Sunset",
            file_path=f"/m/0{i}.wav", bpm=125.0, key="8A",
        ))
    session.commit()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _solar_key(db):
    # Artists differ per track, so the album classifies under "Various Artists".
    return album_key("Solar EP", "Various Artists")


def test_list_sources_reports_modes_and_availability(client):
    res = client.get("/api/albums/sources")
    assert res.status_code == 200
    rows = {s["name"]: s for s in res.json()["sources"]}
    assert set(rows) == {"bandcamp", "musicbrainz", "discogs", "tags"}
    assert rows["bandcamp"]["lookup_mode"] == "url"
    assert rows["discogs"]["available"] is False  # no token in test env


def test_match_source_returns_full_field_diff(client, db):
    key = _solar_key(db)
    candidate = ReleaseCandidate(
        source="bandcamp", source_id="https://x.bandcamp.com/album/solar",
        album="Solar EP", artist="Astral", label="Sunset Records", year=2021,
        recordings=[
            RecordingCandidate(title="Mangled 1", position=1, disc=1),
            RecordingCandidate(title="Mangled 2", position=2, disc=1),
            RecordingCandidate(title="Mangled 3", position=3, disc=1),
        ],
    )
    with patch("kiku.metadata.service.gather_candidates", return_value=[candidate]):
        res = client.post(
            f"/api/albums/{key}/match-source?source=bandcamp",
            json={"url": "https://x.bandcamp.com/album/solar"},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["album"] == "Solar EP"
    assert data["artist"] == "Astral"
    assert data["track_count"] == 3
    # Each track should propose artist + track_number changes.
    item = next(i for i in data["items"] if i["track_id"] == 1)
    changes = {c["field"]: c for c in item["changes"]}
    assert changes["artist"]["new"] == "Astral" and changes["artist"]["changed"] is True
    assert changes["track_number"]["new"] == 1 and changes["track_number"]["changed"] is True


def test_apply_correction_writes_only_allowed_fields_scoped_to_album(client, db):
    key = _solar_key(db)
    res = client.post(
        f"/api/albums/{key}/apply-correction",
        json={
            "source": "bandcamp",
            "source_ref": "https://x.bandcamp.com/album/solar",
            "fields": ["artist", "label"],
            "items": [
                {"track_id": 1, "values": {"artist": "Astral", "label": "Sunset Records",
                                            "release_year": 1999}},
                {"track_id": 999, "values": {"artist": "Hacker"}},  # not in album → ignored
            ],
        },
    )
    assert res.status_code == 200
    assert res.json()["updated_count"] == 1

    t1 = db.get(Track, 1)
    assert t1.artist == "Astral"
    assert t1.label == "Sunset Records"
    assert t1.release_year == 2020  # release_year not in fields allowlist → untouched

    md = db.get(AlbumMetadata, key)
    assert md is not None and md.source == "bandcamp"
    assert md.match_status == "applied"


def test_match_source_unknown_album_is_404(client):
    res = client.post("/api/albums/deadbeef/match-source?source=bandcamp", json={"url": "x"})
    assert res.status_code == 404
