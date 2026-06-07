"""Integration tests for the /api/albums endpoints (list, tracks, MB match/apply)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.api.deps import get_db
from kiku.api.main import create_app
from kiku.db.models import AlbumMetadata, Base, Track


@pytest.fixture()
def albums_db(tmp_path):
    """Three flavors of album: numbered EP, unnumbered LP, compilation."""
    db_path = tmp_path / "albums.db"
    engine = create_engine(f"sqlite:///{db_path}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Album 1: "Solar EP" by "Astral", 3 tracks WITH track_numbers
    for i in range(1, 4):
        session.add(Track(
            id=i,
            title=f"Solar {i}",
            artist="Astral",
            album="Solar EP",
            release_year=2020,
            label="Sunset Records",
            track_number=i,
            disc_number=1,
            file_path=f"/Volumes/SSD/Musica/Astral/Solar EP/0{i} Solar {i}.flac",
            bpm=125.0,
            key="8A",
        ))

    # Album 2: "Long Player" by "Nocturne", 4 tracks WITHOUT track_numbers
    # file_path ordering should govern
    for i, suffix in enumerate(["a Opener", "b Middle", "c Bridge", "d Closer"], start=10):
        session.add(Track(
            id=i,
            title=f"Long {suffix}",
            artist="Nocturne",
            album="Long Player",
            release_year=2018,
            file_path=f"/Musica/Nocturne/{suffix}.flac",
            bpm=120.0,
            key="9A",
        ))

    # Album 3: compilation "Various Vibes" — 3 different artists
    for i, (artist, title) in enumerate([
        ("Alice", "Sunrise"),
        ("Bob", "Noon"),
        ("Charlie", "Dusk"),
    ], start=20):
        session.add(Track(
            id=i,
            title=title,
            artist=artist,
            album="Various Vibes",
            release_year=2022,
            label="Mix Tape Inc",
            file_path=f"/Musica/VA/{i - 19:02d} {title}.flac",
            bpm=128.0,
            key="7A",
        ))

    session.commit()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def albums_client(albums_db):
    app = create_app()

    def override_get_db():
        try:
            yield albums_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_albums_returns_grouped_albums(albums_client) -> None:
    res = albums_client.get("/api/albums")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    by_title = {a["album"]: a for a in data["items"]}

    # EP
    ep = by_title["Solar EP"]
    assert ep["artist"] == "Astral"
    assert ep["track_count"] == 3
    assert ep["year"] == 2020
    assert ep["label"] == "Sunset Records"
    assert ep["is_compilation"] is False
    assert ep["album_key"]  # stable hash

    # LP
    lp = by_title["Long Player"]
    assert lp["artist"] == "Nocturne"
    assert lp["track_count"] == 4
    assert lp["is_compilation"] is False

    # Compilation
    va = by_title["Various Vibes"]
    assert va["artist"] == "Various Artists"
    assert va["is_compilation"] is True


def test_list_albums_search(albums_client) -> None:
    res = albums_client.get("/api/albums", params={"search": "solar"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["album"] == "Solar EP"


def test_list_albums_year_filter(albums_client) -> None:
    res = albums_client.get("/api/albums", params={"year_min": 2020})
    assert res.status_code == 200
    titles = {a["album"] for a in res.json()["items"]}
    assert titles == {"Solar EP", "Various Vibes"}


def test_list_albums_sort_year_desc(albums_client) -> None:
    res = albums_client.get("/api/albums", params={"sort": "year"})
    data = res.json()
    years = [a["year"] for a in data["items"]]
    assert years == sorted(years, key=lambda y: -(y or 0))


def test_album_tracks_uses_track_number_ordering(albums_client) -> None:
    # First get the album_key for Solar EP
    res = albums_client.get("/api/albums", params={"search": "solar"})
    key = res.json()["items"][0]["album_key"]

    res = albums_client.get(f"/api/albums/{key}/tracks")
    assert res.status_code == 200
    data = res.json()
    assert data["album"]["album"] == "Solar EP"
    # Tracks should be ordered by track_number (1, 2, 3)
    track_nums = [t["track_number"] for t in data["tracks"]]
    assert track_nums == [1, 2, 3]


def test_album_tracks_falls_back_to_file_path(albums_client) -> None:
    res = albums_client.get("/api/albums", params={"search": "long player"})
    key = res.json()["items"][0]["album_key"]

    res = albums_client.get(f"/api/albums/{key}/tracks")
    titles = [t["title"] for t in res.json()["tracks"]]
    # Sorted by file_path alphabetically: a, b, c, d
    assert titles == ["Long a Opener", "Long b Middle", "Long c Bridge", "Long d Closer"]


def test_album_tracks_not_found(albums_client) -> None:
    res = albums_client.get("/api/albums/deadbeef0000/tracks")
    assert res.status_code == 404


def test_apply_mb_mapping_writes_track_numbers(albums_client, albums_db) -> None:
    """Applying a mapping should update track_number on Track rows + cache AlbumMetadata."""
    res = albums_client.get("/api/albums", params={"search": "long player"})
    key = res.json()["items"][0]["album_key"]

    # Build mappings for the 4 LP tracks (ids 10..13)
    payload = {
        "mb_release_id": "rel-fake-123",
        "mappings": [
            {"track_id": 10, "mb_position": 1, "track_number": 1, "disc_number": 1, "confidence": 0.95},
            {"track_id": 11, "mb_position": 2, "track_number": 2, "disc_number": 1, "confidence": 0.92},
            {"track_id": 12, "mb_position": 3, "track_number": 3, "disc_number": 1, "confidence": 0.88},
            {"track_id": 13, "mb_position": 4, "track_number": 4, "disc_number": 1, "confidence": 0.90},
        ],
    }
    res = albums_client.post(f"/api/albums/{key}/apply-mb-mapping", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["updated_count"] == 4
    assert body["mb_release_id"] == "rel-fake-123"

    # Verify track numbers were written
    for tid, expected in [(10, 1), (11, 2), (12, 3), (13, 4)]:
        t = albums_db.get(Track, tid)
        assert t.track_number == expected, f"track {tid} should be at position {expected}"

    # Verify album_metadata cache
    md = albums_db.get(AlbumMetadata, key)
    assert md is not None
    assert md.mb_release_id == "rel-fake-123"
    assert md.match_status == "applied"


def test_apply_mb_mapping_ignores_unknown_track_ids(albums_client, albums_db) -> None:
    """track_ids that don't belong to the album are silently skipped."""
    res = albums_client.get("/api/albums", params={"search": "solar"})
    key = res.json()["items"][0]["album_key"]

    payload = {
        "mb_release_id": "rel-x",
        "mappings": [
            {"track_id": 1, "mb_position": 1, "track_number": 1, "disc_number": 1, "confidence": 0.95},
            {"track_id": 9999, "mb_position": 2, "track_number": 2, "disc_number": 1, "confidence": 0.9},
        ],
    }
    res = albums_client.post(f"/api/albums/{key}/apply-mb-mapping", json=payload)
    assert res.status_code == 200
    assert res.json()["updated_count"] == 1  # only track 1 was updated


def test_match_musicbrainz_returns_candidates(albums_client) -> None:
    """MB endpoint returns candidates with mapping preview using mocked client."""
    res = albums_client.get("/api/albums", params={"search": "solar"})
    key = res.json()["items"][0]["album_key"]

    fake_search = [{"id": "mb-rel-1", "score": 95}]
    fake_release = {
        "id": "mb-rel-1",
        "title": "Solar EP",
        "country": "GB",
        "date": "2020-05-01",
        "artist-credit": [{"name": "Astral"}],
        "label-info": [{"label": {"name": "Sunset Records"}}],
        "media": [{
            "position": 1,
            "tracks": [
                {"position": 1, "title": "Solar 1", "length": 200000},
                {"position": 2, "title": "Solar 2", "length": 210000},
                {"position": 3, "title": "Solar 3", "length": 220000},
            ],
        }],
    }

    mock_client = MagicMock()
    mock_client.search_releases.return_value = fake_search
    mock_client.get_release.return_value = fake_release

    with patch(
        "kiku.musicbrainz.client.MusicBrainzClient",
        return_value=mock_client,
    ):
        res = albums_client.post(f"/api/albums/{key}/match-musicbrainz")

    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["candidates"]) == 1
    cand = data["candidates"][0]
    assert cand["mb_release_id"] == "mb-rel-1"
    assert cand["year"] == 2020
    assert cand["country"] == "GB"
    assert cand["label"] == "Sunset Records"
    # Mapping preview should have one entry per Kiku track with high confidence
    assert len(cand["mapping_preview"]) == 3
    confs = [p["confidence"] for p in cand["mapping_preview"]]
    assert all(c >= 0.95 for c in confs)
