"""Unit tests for the best-gap artist pick ranker."""

from __future__ import annotations

from unittest.mock import MagicMock

from kiku.setbuilder.artist_picks import rank_artist_picks


def _track(track_id, artist, key="8A", bpm=124.0, genre="techno", zone="build"):
    t = MagicMock()
    t.id = track_id
    t.artist = artist
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
    # Force the resolved-zone path with a real (zone, source, conf) tuple.
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


def test_ranks_and_caps_n():
    in_set = [_track(1, "Resident"), _track(2, "Resident"), _track(3, "Resident")]
    set_tracks = [_set_track(t, i) for i, t in enumerate(in_set)]
    s = _make_set(set_tracks)
    pool = [_track(10 + i, "Bicep") for i in range(8)]
    session = _make_session(s, pool)
    picks = rank_artist_picks(session, 1, "Bicep", n=3)
    assert len(picks) == 3
    # Sorted descending by score.
    assert picks[0].score >= picks[1].score >= picks[2].score
    # Each pick reports a valid gap (0..len(set)).
    for p in picks:
        assert 0 <= p.position <= len(in_set)
        assert p.reason


def test_excludes_in_set_tracks():
    shared = _track(5, "Bicep")
    in_set = [_track(1, "Resident"), shared, _track(3, "Resident")]
    set_tracks = [_set_track(t, i) for i, t in enumerate(in_set)]
    s = _make_set(set_tracks)
    # Pool returns the in-set Bicep track plus a new one.
    pool = [shared, _track(20, "Bicep")]
    session = _make_session(s, pool)
    picks = rank_artist_picks(session, 1, "Bicep")
    ids = {p.track.id for p in picks}
    assert 5 not in ids
    assert 20 in ids


def test_empty_pool_returns_empty():
    in_set = [_track(1, "Resident"), _track(2, "Resident")]
    set_tracks = [_set_track(t, i) for i, t in enumerate(in_set)]
    s = _make_set(set_tracks)
    session = _make_session(s, [])
    assert rank_artist_picks(session, 1, "Bicep") == []


def test_missing_set_returns_empty():
    session = _make_session(None, [])
    assert rank_artist_picks(session, 999, "Bicep") == []


def test_end_gap_single_neighbor():
    # Single-track set → gaps 0 (before) and 1 (after), each one-neighbor.
    in_set = [_track(1, "Resident")]
    set_tracks = [_set_track(in_set[0], 0)]
    s = _make_set(set_tracks)
    pool = [_track(10, "Bicep")]
    session = _make_session(s, pool)
    picks = rank_artist_picks(session, 1, "Bicep")
    assert len(picks) == 1
    assert picks[0].position in (0, 1)


def test_token_gate_filters_pool():
    # ilike prefilter could return a near-miss; token gate must drop it.
    in_set = [_track(1, "Resident")]
    set_tracks = [_set_track(in_set[0], 0)]
    s = _make_set(set_tracks)
    pool = [_track(10, "Bicepz"), _track(11, "Bicep & Chroma")]
    session = _make_session(s, pool)
    picks = rank_artist_picks(session, 1, "Bicep")
    ids = {p.track.id for p in picks}
    assert ids == {11}
