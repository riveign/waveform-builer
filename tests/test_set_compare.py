"""Tests for the played-vs-planned comparison engine."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.analysis.set_compare import detect_energy_jumps, diff_tracks
from kiku.analysis.teaching import detect_deviation_patterns, deviation_teaching_moment
from kiku.db.models import Base, Set, SetTrack, Track
from kiku.import_playlist.service import suggest_planned_sets


# ── Track diff ──────────────────────────────────────────────────────────


def test_identical_sets_all_kept():
    entries = diff_tracks([1, 2, 3], [1, 2, 3])
    assert [e["kind"] for e in entries] == ["kept", "kept", "kept"]


def test_full_reorder_all_moved_with_displacement():
    entries = diff_tracks([1, 2, 3], [3, 1, 2])
    by_id = {e["track_id"]: e for e in entries}
    assert by_id[3]["kind"] == "moved" and by_id[3]["displacement"] == -2
    assert by_id[1]["kind"] == "moved" and by_id[1]["displacement"] == 1
    assert by_id[2]["kind"] == "moved" and by_id[2]["displacement"] == 1


def test_cut_and_added_mix():
    entries = diff_tracks([1, 2, 3, 4], [1, 9, 3])
    by_id = {e["track_id"]: e for e in entries}
    assert by_id[1]["kind"] == "kept"
    assert by_id[3]["kind"] == "kept"
    assert by_id[9]["kind"] == "added" and by_id[9]["planned_position"] is None
    assert by_id[2]["kind"] == "cut" and by_id[2]["played_position"] is None
    assert by_id[4]["kind"] == "cut"


def test_duplicate_track_ids_pair_in_order():
    entries = diff_tracks([7, 7], [7])
    kinds = sorted(e["kind"] for e in entries)
    assert kinds == ["cut", "kept"]


def test_empty_planned_all_added():
    entries = diff_tracks([], [1, 2])
    assert [e["kind"] for e in entries] == ["added", "added"]


# ── Energy jumps ────────────────────────────────────────────────────────


def test_energy_jump_detection():
    planned = [0.3, 0.4, 0.5, 0.6]
    played = [0.3, 0.75, 0.5, 0.25]
    jumps = detect_energy_jumps(planned, played)
    assert (1, 0.35) in jumps
    assert (3, -0.35) in jumps
    assert all(pos not in (0, 2) for pos, _ in jumps)


def test_no_jumps_when_curves_track():
    assert detect_energy_jumps([0.3, 0.5], [0.35, 0.45]) == []


# ── Deviation teaching moments ──────────────────────────────────────────


@pytest.mark.parametrize("kind", ["kept", "moved", "cut", "added", "energy_jump"])
def test_deviation_moment_never_blames(kind):
    moment = deviation_teaching_moment(
        kind, title="Test Track", displacement=2, delta=0.4, position=3
    )
    assert moment
    for word in ("mistake", "wrong", "failed", "blame"):
        assert word not in moment.lower()


def test_moved_earlier_mentions_floor():
    moment = deviation_teaching_moment("moved", title="Peak Tune", displacement=-3)
    assert "earlier" in moment


def test_added_frames_instinct():
    moment = deviation_teaching_moment("added", title="Secret Weapon")
    assert "wasn't in the plan" in moment


# ── Deviation patterns ──────────────────────────────────────────────────


def test_all_kept_pattern():
    devs = [("kept", 0), ("kept", 1), ("kept", 2)]
    patterns = detect_deviation_patterns(devs, [0.0, 0.0, 0.0], 3)
    assert len(patterns) == 1
    assert "exactly as planned" in patterns[0]


def test_late_adds_pattern():
    devs = [("kept", 0), ("kept", 1), ("added", 8), ("added", 9)]
    patterns = detect_deviation_patterns(devs, [], 10)
    assert any("cluster late" in p for p in patterns)


def test_heavy_cuts_pattern():
    devs = [("kept", 0), ("cut", None), ("cut", None)]
    patterns = detect_deviation_patterns(devs, [], 1)
    assert any("cut over a third" in p for p in patterns)


def test_running_hot_pattern():
    devs = [("kept", 0), ("moved", 1)]
    patterns = detect_deviation_patterns(devs, [0.2, 0.3, 0.25], 3)
    assert any("hotter than the plan" in p for p in patterns)


# ── Candidate suggestion (Jaccard) ──────────────────────────────────────


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    for i in range(1, 11):
        s.add(Track(id=i, title=f"Track {i}", bpm=120.0 + i, duration_sec=300.0))
    a = Set(id=1, name="Planned A", source="kiku")
    b = Set(id=2, name="Planned B", source="kiku")
    c = Set(id=3, name="Manual", source="manual")
    s.add_all([a, b, c])
    s.flush()
    for pos, tid in enumerate([1, 2, 3, 4, 5]):
        s.add(SetTrack(set_id=1, position=pos, track_id=tid))
    for pos, tid in enumerate([6, 7, 8]):
        s.add(SetTrack(set_id=2, position=pos, track_id=tid))
    for pos, tid in enumerate([1, 2, 3]):
        s.add(SetTrack(set_id=3, position=pos, track_id=tid))
    s.commit()
    yield s
    s.close()
    engine.dispose()


def test_suggest_planned_sets_ranks_by_overlap(session):
    candidates = suggest_planned_sets(session, [1, 2, 3, 4, 5])
    assert candidates[0]["set_id"] == 1
    assert candidates[0]["overlap"] == 1.0
    assert candidates[0]["shared_tracks"] == 5


def test_suggest_planned_sets_threshold_excludes_weak(session):
    # One shared track each side -> Jaccard well below 0.3
    candidates = suggest_planned_sets(session, [1, 6, 9, 10])
    assert candidates == []


def test_suggest_planned_sets_ignores_non_kiku_sets(session):
    candidates = suggest_planned_sets(session, [1, 2, 3])
    assert all(c["set_id"] != 3 for c in candidates)


def test_suggest_planned_sets_excludes_self(session):
    candidates = suggest_planned_sets(session, [1, 2, 3, 4, 5], exclude_set_id=1)
    assert all(c["set_id"] != 1 for c in candidates)
