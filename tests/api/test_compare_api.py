"""API tests for played-vs-planned link + compare endpoints."""

from kiku.db.models import Set, SetTrack


def _seed_planned_set(db_session, set_id=2, track_ids=(1, 2, 3, 4, 5)):
    planned = Set(id=set_id, name="Planned Set", source="kiku", duration_min=30)
    db_session.add(planned)
    db_session.flush()
    for pos, tid in enumerate(track_ids):
        db_session.add(SetTrack(set_id=set_id, position=pos, track_id=tid))
    db_session.commit()
    return planned


# ── Link / unlink ──────────────────────────────────────────────────────


def test_link_sets(client, db_session):
    _seed_planned_set(db_session)
    res = client.put("/api/sets/1/link", json={"planned_set_id": 2})
    assert res.status_code == 200
    assert res.json() == {"set_id": 1, "planned_set_id": 2}


def test_link_self_returns_400(client, db_session):
    res = client.put("/api/sets/1/link", json={"planned_set_id": 1})
    assert res.status_code == 400


def test_link_missing_planned_returns_404(client, db_session):
    res = client.put("/api/sets/1/link", json={"planned_set_id": 999})
    assert res.status_code == 404


def test_link_missing_set_returns_404(client, db_session):
    res = client.put("/api/sets/999/link", json={"planned_set_id": 1})
    assert res.status_code == 404


def test_unlink(client, db_session):
    _seed_planned_set(db_session)
    client.put("/api/sets/1/link", json={"planned_set_id": 2})
    res = client.delete("/api/sets/1/link")
    assert res.status_code == 204
    assert db_session.get(Set, 1).planned_set_id is None


def test_set_detail_exposes_link(client, db_session):
    _seed_planned_set(db_session)
    client.put("/api/sets/1/link", json={"planned_set_id": 2})
    res = client.get("/api/sets/1")
    assert res.status_code == 200
    assert res.json()["planned_set_id"] == 2


# ── Compare ────────────────────────────────────────────────────────────


def test_compare_unlinked_returns_404(client, db_session):
    res = client.post("/api/sets/1/compare")
    assert res.status_code == 404


def test_compare_returns_report_and_caches(client, db_session):
    # Played set 1 has tracks 1-5; plan has 1,2,3 then 6,7 -> 3 kept, 2 added, 2 cut
    _seed_planned_set(db_session, track_ids=(1, 2, 3, 6, 7))
    client.put("/api/sets/1/link", json={"planned_set_id": 2})
    res = client.post("/api/sets/1/compare")
    assert res.status_code == 200
    data = res.json()
    assert data["kept_count"] == 3
    assert data["added_count"] == 2
    assert data["cut_count"] == 2
    assert data["planned_set_id"] == 2
    assert len(data["track_deviations"]) == 7
    assert all(d["teaching_moment"] for d in data["track_deviations"])
    assert len(data["arc"]["planned_curve"]) == 5
    assert len(data["arc"]["played_curve"]) == 5
    # Cached and served by GET
    cached = client.get("/api/sets/1/comparison")
    assert cached.status_code == 200
    assert cached.json()["kept_count"] == 3


def test_comparison_404_before_compare(client, db_session):
    res = client.get("/api/sets/1/comparison")
    assert res.status_code == 404


def test_track_mutation_invalidates_comparison(client, db_session):
    _seed_planned_set(db_session)
    client.put("/api/sets/1/link", json={"planned_set_id": 2})
    assert client.post("/api/sets/1/compare").status_code == 200
    assert client.get("/api/sets/1/comparison").status_code == 200
    # Mutating the played set clears its cached comparison
    res = client.post("/api/sets/1/tracks", json={"track_id": 10, "position": 5})
    assert res.status_code == 200
    assert client.get("/api/sets/1/comparison").status_code == 404


def test_planned_mutation_invalidates_comparison_on_played_side(client, db_session):
    _seed_planned_set(db_session)
    client.put("/api/sets/1/link", json={"planned_set_id": 2})
    assert client.post("/api/sets/1/compare").status_code == 200
    # Mutating the PLANNED set clears the played set's cache (reverse lookup)
    res = client.post("/api/sets/2/tracks", json={"track_id": 10, "position": 5})
    assert res.status_code == 200
    assert client.get("/api/sets/1/comparison").status_code == 404
