"""Tests for Track Hunter API endpoints."""

from __future__ import annotations


def test_list_hunts(client):
    """GET /api/hunts returns seeded hunt sessions."""
    resp = client.get("/api/hunts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["platform"] == "youtube"
    assert data["items"][0]["track_count"] == 3
    assert data["items"][0]["owned_count"] == 1


def test_get_hunt_detail(client):
    """GET /api/hunt/1 returns full hunt with tracks."""
    resp = client.get("/api/hunt/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test DJ Set"
    assert len(data["tracks"]) == 3
    assert data["tracks"][0]["acquisition_status"] == "owned"
    assert data["tracks"][1]["acquisition_status"] == "unowned"


def test_get_hunt_not_found(client):
    """GET /api/hunt/999 returns 404."""
    resp = client.get("/api/hunt/999")
    assert resp.status_code == 404


def test_update_hunt_track_status(client):
    """PATCH /api/hunt/tracks/{id} updates acquisition status."""
    # Get track 2 (unowned) and mark as wanted
    resp = client.get("/api/hunt/1")
    track_id = resp.json()["tracks"][1]["id"]

    resp = client.patch(
        f"/api/hunt/tracks/{track_id}",
        json={"acquisition_status": "wanted"},
    )
    assert resp.status_code == 200
    assert resp.json()["acquisition_status"] == "wanted"


def test_update_hunt_track_invalid_status(client):
    """PATCH with invalid status returns 400."""
    resp = client.get("/api/hunt/1")
    track_id = resp.json()["tracks"][0]["id"]

    resp = client.patch(
        f"/api/hunt/tracks/{track_id}",
        json={"acquisition_status": "invalid"},
    )
    assert resp.status_code == 400


def test_hunt_track_purchase_links(client):
    """Hunt tracks with purchase links return them as dicts."""
    resp = client.get("/api/hunt/1")
    tracks = resp.json()["tracks"]
    # Track 2 has beatport link
    unowned = [t for t in tracks if t["acquisition_status"] != "owned"]
    assert len(unowned) >= 1
    assert "beatport" in unowned[0]["purchase_links"] or "bandcamp" in unowned[0]["purchase_links"]
