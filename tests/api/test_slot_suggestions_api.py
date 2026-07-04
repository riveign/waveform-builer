"""Integration tests for GET /api/sets/{set_id}/slots/{position}/suggestions."""

from __future__ import annotations

from kiku.db.models import Track


def test_brighten_insert_ranked(client):
    # Insert at slot 1 → prev = track 2 (8A) → brighten targets 8B; seed's
    # odd-id 8B tracks (not in set) qualify.
    resp = client.get(
        "/api/sets/1/slots/1/suggestions",
        params={"mode": "insert", "intent": "brighten"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["set_id"] == 1
    assert body["position"] == 1
    assert body["mode"] == "insert"
    assert body["intent"] == "brighten"
    suggestions = body["suggestions"]
    assert len(suggestions) >= 1
    ids = {sg["track"]["id"] for sg in suggestions}
    assert ids.isdisjoint({1, 2, 3, 4, 5})  # in-set tracks excluded
    for sg in suggestions:
        assert sg["move"]  # Show the Why — never a bare ranked list
        assert "caveat" in sg
    scores = [sg["score"] for sg in suggestions]
    assert scores == sorted(scores, reverse=True)


def test_hold_ranked(client):
    resp = client.get(
        "/api/sets/1/slots/2/suggestions",
        params={"mode": "insert", "intent": "hold"},
    )
    assert resp.status_code == 200
    assert len(resp.json()["suggestions"]) >= 1


def test_push_higher_warm_empty_on_default_seed(client):
    # prev key is 8A → push_higher needs a 9A candidate; the seed has none.
    resp = client.get(
        "/api/sets/1/slots/1/suggestions",
        params={"mode": "insert", "intent": "push_higher"},
    )
    assert resp.status_code == 200
    assert resp.json()["suggestions"] == []


def test_push_higher_with_seeded_key(client, db_session):
    # Add a purpose-keyed 9A track in the neighbours' BPM window.
    db_session.add(Track(
        id=99, title="Lift", artist="Purpose", bpm=123.0, key="9A",
        dir_genre="techno", dir_energy="high", duration_sec=320.0,
        rating=4, play_count=5, kiku_play_count=1,
    ))
    db_session.commit()
    resp = client.get(
        "/api/sets/1/slots/1/suggestions",
        params={"mode": "insert", "intent": "push_higher"},
    )
    assert resp.status_code == 200
    ids = {sg["track"]["id"] for sg in resp.json()["suggestions"]}
    assert 99 in ids


def test_missing_set_404(client):
    resp = client.get(
        "/api/sets/9999/slots/0/suggestions",
        params={"mode": "insert", "intent": "hold"},
    )
    assert resp.status_code == 404


def test_invalid_mode_400(client):
    resp = client.get(
        "/api/sets/1/slots/0/suggestions",
        params={"mode": "sideways", "intent": "hold"},
    )
    assert resp.status_code == 400


def test_invalid_intent_400(client):
    resp = client.get(
        "/api/sets/1/slots/0/suggestions",
        params={"mode": "insert", "intent": "levitate"},
    )
    assert resp.status_code == 400


def test_out_of_range_position_404(client):
    resp = client.get(
        "/api/sets/1/slots/99/suggestions",
        params={"mode": "insert", "intent": "hold"},
    )
    assert resp.status_code == 404
