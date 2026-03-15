"""Tests for set API endpoints."""

from __future__ import annotations


def test_list_sets(client):
    resp = client.get("/api/sets")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Test Set"


def test_set_detail(client):
    resp = client.get("/api/sets/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert len(data["tracks"]) == 5


def test_set_detail_not_found(client):
    resp = client.get("/api/sets/999")
    assert resp.status_code == 404


def test_create_set(client):
    resp = client.post("/api/sets", json={"name": "New Set"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New Set"
    assert data["track_count"] == 0
    assert "id" in data


def test_create_set_with_options(client):
    resp = client.post("/api/sets", json={
        "name": "Filtered Set",
        "energy_profile": "warmup:30:0.3,peak:30:0.9",
        "genre_filter": ["techno", "house"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Filtered Set"


def test_update_set(client):
    resp = client.put("/api/sets/1", json={"name": "Renamed Set"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Renamed Set"
    assert data["id"] == 1


def test_update_set_not_found(client):
    resp = client.put("/api/sets/999", json={"name": "Nope"})
    assert resp.status_code == 404


def test_delete_set(client):
    # Create a set to delete
    create_resp = client.post("/api/sets", json={"name": "To Delete"})
    set_id = create_resp.json()["id"]

    resp = client.delete(f"/api/sets/{set_id}")
    assert resp.status_code == 204

    # Confirm it's gone
    resp = client.get(f"/api/sets/{set_id}")
    assert resp.status_code == 404


def test_delete_set_not_found(client):
    resp = client.delete("/api/sets/999")
    assert resp.status_code == 404


def test_build_set_sse(client):
    resp = client.post("/api/sets/build", json={
        "name": "Built Set",
        "duration_min": 30,
        "energy_preset": "journey",
        "beam_width": 2,
    })
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    # Parse SSE events
    body = resp.text
    assert "event: started" in body
    # Should have either complete or error
    assert "event: complete" in body or "event: error" in body


def test_build_set_sse_bad_seed(client):
    resp = client.post("/api/sets/build", json={
        "name": "Bad Seed",
        "seed_track_id": 99999,
    })
    assert resp.status_code == 200
    body = resp.text
    assert "event: error" in body
    assert "Seed track not found" in body


# ── Track mutation tests ──


def test_add_track_to_set(client):
    """POST track appends to end of set."""
    # Set 1 has tracks 1-5 seeded at positions 1-5
    resp = client.post("/api/sets/1/tracks", json={"track_id": 10})
    assert resp.status_code == 200
    tracks = resp.json()
    assert len(tracks) == 6
    # Track 10 should be present in the set
    track_ids = [t["track_id"] for t in tracks]
    assert 10 in track_ids


def test_remove_track_from_set(client):
    """DELETE track removes it and re-compacts positions."""
    resp = client.delete("/api/sets/1/tracks/3")
    assert resp.status_code in (200, 204)
    # Verify track 3 is gone
    detail = client.get("/api/sets/1").json()
    track_ids = [t["track_id"] for t in detail["tracks"]]
    assert 3 not in track_ids
    assert len(detail["tracks"]) == 4


def test_reorder_set_tracks(client):
    """PUT reorder changes track order."""
    new_order = [5, 4, 3, 2, 1]
    resp = client.put("/api/sets/1/tracks/reorder", json={"track_ids": new_order})
    assert resp.status_code == 200
    tracks = resp.json()
    result_ids = [t["track_id"] for t in sorted(tracks, key=lambda t: t["position"])]
    assert result_ids == new_order
