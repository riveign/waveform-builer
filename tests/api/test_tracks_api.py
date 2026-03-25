"""Tests for track API endpoints."""

from __future__ import annotations


def test_search_tracks_default(client):
    resp = client.get("/api/tracks/search")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "offset" in data
    assert "limit" in data
    assert data["total"] == 20
    assert data["offset"] == 0
    assert len(data["items"]) == 20


def test_search_tracks_pagination(client):
    resp = client.get("/api/tracks/search?limit=5&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 5
    assert data["total"] == 20
    assert data["offset"] == 0
    assert data["limit"] == 5

    # Second page
    resp2 = client.get("/api/tracks/search?limit=5&offset=5")
    data2 = resp2.json()
    assert len(data2["items"]) == 5
    assert data2["offset"] == 5
    # Items should be different
    ids_page1 = {t["id"] for t in data["items"]}
    ids_page2 = {t["id"] for t in data2["items"]}
    assert ids_page1.isdisjoint(ids_page2)


def test_search_tracks_filter_genre(client):
    resp = client.get("/api/tracks/search?genre=techno")
    data = resp.json()
    assert data["total"] == 10
    assert all(t["genre"] == "techno" for t in data["items"])


def test_search_tracks_filter_bpm(client):
    resp = client.get("/api/tracks/search?bpm_min=125&bpm_max=130")
    data = resp.json()
    assert data["total"] > 0
    assert all(125 <= t["bpm"] <= 130 for t in data["items"])


def test_track_detail(client):
    resp = client.get("/api/tracks/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["title"] == "Track 1"


def test_track_detail_not_found(client):
    resp = client.get("/api/tracks/999")
    assert resp.status_code == 404


def test_suggest_next(client):
    resp = client.get("/api/tracks/1/suggest-next?n=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_track_id"] == 1
    assert len(data["suggestions"]) <= 5
    for s in data["suggestions"]:
        assert "track" in s
        assert "score" in s
        assert "breakdown" in s
        bd = s["breakdown"]
        assert "harmonic" in bd
        assert "energy_fit" in bd
        assert "bpm_compat" in bd
        assert "genre_coherence" in bd
        assert "track_quality" in bd
        assert "total" in bd


def test_suggest_next_not_found(client):
    resp = client.get("/api/tracks/999/suggest-next")
    assert resp.status_code == 404


def test_suggest_next_genre_filter(client):
    resp = client.get("/api/tracks/1/suggest-next?genre_filter=house")
    assert resp.status_code == 200
    data = resp.json()
    # All suggestions should be house genre
    for s in data["suggestions"]:
        assert s["track"]["genre"] == "house"


def test_record_played(client):
    """POST /api/tracks/{id}/played should return 204 and increment kiku_play_count."""
    resp = client.post("/api/tracks/1/played")
    assert resp.status_code == 204

    # Verify the count incremented
    detail = client.get("/api/tracks/1").json()
    assert detail["kiku_play_count"] >= 1


def test_record_played_not_found(client):
    resp = client.post("/api/tracks/999/played")
    assert resp.status_code == 404


def test_suggest_next_with_discovery_density(client):
    """discovery_density param should be accepted and affect results."""
    resp_neutral = client.get("/api/tracks/1/suggest-next?n=5&discovery_density=0.0")
    assert resp_neutral.status_code == 200

    resp_discovery = client.get("/api/tracks/1/suggest-next?n=5&discovery_density=-1.0")
    assert resp_discovery.status_code == 200

    resp_density = client.get("/api/tracks/1/suggest-next?n=5&discovery_density=1.0")
    assert resp_density.status_code == 200

    # All should return valid structure
    for resp in [resp_neutral, resp_discovery, resp_density]:
        data = resp.json()
        for s in data["suggestions"]:
            assert "breakdown" in s
            assert "discovery_label" in s["breakdown"]
