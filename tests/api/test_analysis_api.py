"""API tests for set analysis endpoints."""

from __future__ import annotations


def test_analyze_set(client):
    """POST /api/sets/1/analyze should return analysis with transitions."""
    res = client.post("/api/sets/1/analyze")
    assert res.status_code == 200
    data = res.json()
    assert data["set_id"] == 1
    assert data["track_count"] == 5
    assert data["transition_count"] == 4
    assert len(data["transitions"]) == 4
    assert "arc" in data
    assert "overall_score" in data
    assert "analyzed_at" in data

    # Verify transition structure
    t0 = data["transitions"][0]
    assert "scores" in t0
    assert "teaching_moment" in t0
    assert t0["position"] == 0


def test_get_cached_analysis(client):
    """GET /api/sets/1/analysis should return cached analysis after analyze."""
    # First analyze
    client.post("/api/sets/1/analyze")
    # Then fetch cached
    res = client.get("/api/sets/1/analysis")
    assert res.status_code == 200
    data = res.json()
    assert data["set_id"] == 1
    assert data["track_count"] == 5


def test_get_analysis_not_analyzed(client):
    """GET /api/sets/1/analysis should 404 before any analysis."""
    res = client.get("/api/sets/1/analysis")
    assert res.status_code == 404


def test_analyze_nonexistent_set(client):
    """POST /api/sets/999/analyze should 404."""
    res = client.post("/api/sets/999/analyze")
    assert res.status_code == 404
