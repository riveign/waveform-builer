"""Unit tests for the directional slot-pick ranker."""

from __future__ import annotations

from unittest.mock import MagicMock

from kiku.setbuilder.slot_picks import rank_slot_picks


def _track(track_id, key="8A", bpm=124.0, genre="techno", zone="build"):
    t = MagicMock()
    t.id = track_id
    t.artist = f"Artist {track_id}"
    t.title = f"Track {track_id}"
    t.key = key
    t.bpm = bpm
    t.dir_genre = genre
    t.rb_genre = genre
    t.dir_energy = "mid"
    t.energy_predicted = None
    t.rating = 3
    t.play_count = 0
    t.kiku_play_count = 0
    t.playlist_tags = None
    # Scoring reads audio_features.energy first, then resolved_energy_zone.
    t.audio_features = None
    t.resolved_energy_zone = (zone, "dir_energy", 0.6)
    return t


def _set_track(track, position):
    st = MagicMock()
    st.track = track
    st.track_id = track.id
    st.position = position
    return st


def _make_session(set_obj, pool):
    """Fake session: .get(Set, id) -> set_obj; query(Track)...all() -> pool."""
    session = MagicMock()
    session.get.return_value = set_obj
    query = MagicMock()
    query.filter.return_value = query
    query.all.return_value = pool
    session.query.return_value = query
    return session


def _make_set(set_tracks, energy_profile=None, duration_min=60):
    s = MagicMock()
    s.tracks = set_tracks
    s.energy_profile = energy_profile
    s.duration_min = duration_min
    return s


def test_missing_set_returns_empty():
    session = _make_session(None, [])
    assert rank_slot_picks(session, 999, 0, "insert", "hold") == []


def test_out_of_range_position_returns_empty():
    in_set = [_track(1), _track(2)]
    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
    session = _make_session(s, [_track(10)])
    assert rank_slot_picks(session, 1, 9, "insert", "hold") == []


def test_insert_mode_neighbors_and_ranking():
    in_set = [_track(1, key="8A"), _track(2, key="8A"), _track(3, key="8A")]
    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
    pool = [_track(10 + i, key="8A") for i in range(6)]
    session = _make_session(s, pool)
    picks = rank_slot_picks(session, 1, 1, "insert", "hold", n=3)
    assert len(picks) == 3
    assert picks[0].score >= picks[1].score >= picks[2].score
    for p in picks:
        assert p.caveat is None  # hold never trips the caveat


def test_replace_excludes_in_set_track():
    shared = _track(2, key="8A")
    in_set = [_track(1, key="8A"), shared, _track(3, key="8A")]
    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
    # ilike/BPM prefilter could hand back an in-set track — exclusion must drop it.
    pool = [shared, _track(20, key="8A")]
    session = _make_session(s, pool)
    picks = rank_slot_picks(session, 1, 1, "replace", "hold")
    ids = {p.track.id for p in picks}
    assert 2 not in ids
    assert 20 in ids


def test_allowed_keys_hard_filter():
    in_set = [_track(1, key="8A"), _track(2, key="8A"), _track(3, key="8A")]
    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
    pool = [_track(10, key="9A"), _track(11, key="8B"), _track(12, key="9A")]
    session = _make_session(s, pool)
    picks = rank_slot_picks(
        session, 1, 1, "replace", "hold", allowed_keys={"9A"}
    )
    assert {p.track.id for p in picks} == {10, 12}


def test_energy_shift_reranks():
    # Two candidates identical but for energy zone; the shift decides the order.
    in_set = [_track(1, key="8A"), _track(2, key="8A"), _track(3, key="8A")]
    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
    hot = _track(10, key="8A", zone="peak")
    cool = _track(11, key="8A", zone="warmup")
    session = _make_session(s, [hot, cool])
    # Shift the target UP → the hotter track ranks first.
    up = rank_slot_picks(session, 1, 1, "replace", "hold", energy_delta=0.4)
    assert up[0].track.id == 10
    # Shift the target DOWN → the cooler track ranks first.
    down = rank_slot_picks(session, 1, 1, "replace", "hold", energy_delta=-0.4)
    assert down[0].track.id == 11


def test_caveat_names_achievable_alt():
    # prev 8A, next 7B: a push_higher (candidate 9A) mixes clean out of 8A
    # (0.85) but clashes into 7B (0.2) — the alt brighten (8A→8B) keeps both
    # sides >= 0.8, so the caveat must recommend brighten to 8B.
    in_set = [_track(1, key="8A"), _track(2, key="10A"), _track(3, key="7B")]
    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
    pool = [_track(10, key="9A")]  # matches push_higher's allowed key {9A}
    session = _make_session(s, pool)
    picks = rank_slot_picks(session, 1, 1, "replace", "push_higher")
    assert len(picks) == 1
    assert picks[0].caveat is not None
    assert "brighten" in picks[0].caveat
    assert "8B" in picks[0].caveat


def test_no_caveat_when_both_sides_clean():
    # prev 8A, next 9A: push_higher candidate 9A mixes 0.85 out, 1.0 in — clean.
    in_set = [_track(1, key="8A"), _track(2, key="10A"), _track(3, key="9A")]
    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
    pool = [_track(10, key="9A")]
    session = _make_session(s, pool)
    picks = rank_slot_picks(session, 1, 1, "replace", "push_higher")
    assert len(picks) == 1
    assert picks[0].caveat is None


def test_end_slot_single_neighbor():
    # Insert at the last slot → prev = last track, next = None (one neighbor).
    in_set = [_track(1, key="8A"), _track(2, key="8A")]
    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
    pool = [_track(10, key="8A")]
    session = _make_session(s, pool)
    picks = rank_slot_picks(session, 1, 1, "insert", "hold")
    assert len(picks) == 1
    assert picks[0].caveat is None  # no successor to assess
