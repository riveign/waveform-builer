"""Tests for Energy Tinder API endpoints."""

from __future__ import annotations


def test_tinder_queue_returns_items(client):
    resp = client.get("/api/tinder/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 10
    assert len(data["items"]) == 10
    # First item should have lowest confidence (0.1)
    assert data["items"][0]["energy_confidence"] < data["items"][-1]["energy_confidence"]


def test_tinder_queue_pagination(client):
    resp = client.get("/api/tinder/queue?limit=3&offset=0")
    data = resp.json()
    assert len(data["items"]) == 3
    assert data["total"] == 10
    assert data["offset"] == 0


def test_tinder_queue_filter_bpm(client):
    resp = client.get("/api/tinder/queue?bpm_min=125&bpm_max=130")
    data = resp.json()
    assert data["total"] > 0
    for item in data["items"]:
        assert 125 <= item["track"]["bpm"] <= 130


def test_tinder_decide_confirm(client):
    resp = client.post("/api/tinder/decide", json={
        "track_id": 1,
        "decision": "confirm",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "confirm"
    assert data["applied_zone"] is not None


def test_tinder_decide_override(client):
    resp = client.post("/api/tinder/decide", json={
        "track_id": 2,
        "decision": "override",
        "override_zone": "warmup",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "override"
    assert data["applied_zone"] == "warmup"


def test_tinder_decide_skip(client):
    resp = client.post("/api/tinder/decide", json={
        "track_id": 3,
        "decision": "skip",
    })
    assert resp.status_code == 200
    assert resp.json()["decision"] == "skip"


def test_tinder_decide_not_found(client):
    resp = client.post("/api/tinder/decide", json={
        "track_id": 9999,
        "decision": "confirm",
    })
    assert resp.status_code == 404


def test_tinder_decide_invalid_decision(client):
    resp = client.post("/api/tinder/decide", json={
        "track_id": 1,
        "decision": "yolo",
    })
    assert resp.status_code == 400


def test_tinder_stats(client):
    resp = client.get("/api/tinder/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "queue_remaining" in data
    assert "total_reviewed" in data
