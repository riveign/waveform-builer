"""Integration tests for GET /api/sets/{set_id}/artist-picks."""

from __future__ import annotations


def test_artist_picks_ranked(client):
    # "Artist 2" owns tracks 1,6,11,16; track 1 is in set 1, so 6/11/16 are new.
    resp = client.get("/api/sets/1/artist-picks", params={"artist": "Artist 2"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["set_id"] == 1
    assert body["artist"] == "Artist 2"
    picks = body["picks"]
    assert len(picks) >= 1
    # No in-set track leaks in (track 1 belongs to Artist 2 but is in the set).
    ids = {p["track"]["id"] for p in picks}
    assert 1 not in ids
    # Every pick carries a placement + reason (Show the Why).
    for p in picks:
        assert isinstance(p["position"], int)
        assert p["reason"]
    # Ranked descending.
    scores = [p["score"] for p in picks]
    assert scores == sorted(scores, reverse=True)


def test_artist_picks_n_cap(client):
    resp = client.get(
        "/api/sets/1/artist-picks", params={"artist": "Artist 2", "n": 2}
    )
    assert resp.status_code == 200
    assert len(resp.json()["picks"]) <= 2


def test_artist_picks_missing_set_404(client):
    resp = client.get("/api/sets/9999/artist-picks", params={"artist": "Artist 2"})
    assert resp.status_code == 404


def test_artist_picks_no_new_tracks_empty(client):
    # Unknown artist owns nothing → 200 with empty picks (warm, not an error).
    resp = client.get(
        "/api/sets/1/artist-picks", params={"artist": "Nonexistent Artist"}
    )
    assert resp.status_code == 200
    assert resp.json()["picks"] == []
