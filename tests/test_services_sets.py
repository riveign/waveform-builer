"""Tests for the set use-cases.

The point of this layer is that the API and the CLI cannot drift apart, so the
tests that matter most are the ones on `resolve` — the behaviour that used to be
copy-pasted into five CLI commands — and on the error types, which are the
contract each transport translates.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.db.models import Base, Set, SetTrack, Track
from kiku.services import sets as svc


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 's.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture()
def seeded(session):
    for i in range(1, 6):
        session.add(
            Track(id=i, title=f"Track {i}", artist=f"A{i}", bpm=124.0, key="8A", duration_sec=360.0)
        )
    session.add(Set(id=1, name="Birthday Raw Energy", duration_min=60))
    session.add(Set(id=2, name="Sunday Warmup", duration_min=90))
    session.flush()
    for pos, tid in enumerate([1, 2, 3]):
        session.add(SetTrack(set_id=1, position=pos, track_id=tid))
    session.commit()
    return session


# ── resolve: the use-case that was written five times ──────────────────


def test_resolve_by_id(seeded):
    assert svc.resolve(seeded, 1).name == "Birthday Raw Energy"


def test_resolve_by_numeric_string(seeded):
    """The CLI hands over whatever the DJ typed, so "1" must work like 1."""
    assert svc.resolve(seeded, "1").id == 1


def test_resolve_by_partial_name(seeded):
    assert svc.resolve(seeded, "Birthday").id == 1


def test_resolve_by_name_is_case_insensitive(seeded):
    assert svc.resolve(seeded, "sunday").id == 2


def test_resolve_raises_with_the_reference_in_the_message(seeded):
    with pytest.raises(svc.SetNotFound, match="nonexistent"):
        svc.resolve(seeded, "nonexistent")


def test_resolve_raises_for_an_unknown_id(seeded):
    with pytest.raises(svc.SetNotFound):
        svc.resolve(seeded, 999)


# ── get ────────────────────────────────────────────────────────────────


def test_get_raises_rather_than_returning_none(seeded):
    with pytest.raises(svc.SetNotFound):
        svc.get(seeded, 999)


# ── lifecycle ──────────────────────────────────────────────────────────


def test_create_serialises_the_genre_filter(session):
    created = svc.create(session, name="New", genre_filter=["techno", "house"])

    assert created.id is not None
    assert json.loads(created.genre_filter) == ["techno", "house"]


def test_update_only_touches_what_was_given(seeded):
    svc.update(seeded, 1, name="Renamed")
    s = svc.get(seeded, 1)

    assert s.name == "Renamed"
    assert s.duration_min == 60, "an unrelated field was overwritten"


def test_soft_delete_hides_without_destroying(seeded):
    svc.soft_delete(seeded, 1)

    assert svc.get(seeded, 1).deleted_at is not None
    assert 1 not in [s.id for s in svc.list_active(seeded)]
    assert 1 in [s.id for s in svc.list_trashed(seeded)]


def test_restore_brings_it_back(seeded):
    svc.soft_delete(seeded, 1)
    svc.restore(seeded, 1)

    assert 1 in [s.id for s in svc.list_active(seeded)]


def test_purge_removes_only_sets_past_the_grace_period(seeded):
    fresh = svc.get(seeded, 1)
    fresh.deleted_at = datetime.now().isoformat()
    stale = svc.get(seeded, 2)
    stale.deleted_at = (datetime.now() - timedelta(days=svc.SOFT_DELETE_DAYS + 1)).isoformat()
    seeded.commit()

    purged = svc.purge_expired(seeded)

    assert purged == 1
    assert seeded.get(Set, 1) is not None, "a recently trashed set was destroyed"
    assert seeded.get(Set, 2) is None


def test_listing_purges_expired_sets_on_the_way_past(seeded):
    """The trash empties itself as a side effect of being looked at, which is why
    no scheduled job exists."""
    stale = svc.get(seeded, 2)
    stale.deleted_at = (datetime.now() - timedelta(days=svc.SOFT_DELETE_DAYS + 1)).isoformat()
    seeded.commit()

    svc.list_active(seeded)

    assert seeded.get(Set, 2) is None


def test_list_active_filters_by_name(seeded):
    assert [s.id for s in svc.list_active(seeded, search="Sunday")] == [2]


# ── caches ─────────────────────────────────────────────────────────────


def test_invalidating_analysis_clears_the_cache_and_the_flag(seeded):
    s = svc.get(seeded, 1)
    s.is_analyzed = 1
    s.analysis_cache = '{"stale": true}'
    seeded.commit()

    svc.invalidate_analysis(seeded, s)

    assert s.is_analyzed == 0
    assert s.analysis_cache is None


def test_clearing_comparisons_reaches_played_sets_linked_to_this_plan(seeded):
    """Editing a plan invalidates the comparison held by the *played* set pointing
    at it — the cache lives on the other side of the link."""
    played = svc.get(seeded, 2)
    played.planned_set_id = 1
    played.comparison_cache = '{"stale": true}'
    seeded.commit()

    svc.clear_comparison_caches(seeded, svc.get(seeded, 1))

    assert svc.get(seeded, 2).comparison_cache is None


# ── link / compare ─────────────────────────────────────────────────────


def test_link_records_the_plan(seeded):
    svc.link_to_plan(seeded, 2, 1)

    assert svc.get(seeded, 2).planned_set_id == 1


def test_a_set_cannot_be_its_own_plan(seeded):
    with pytest.raises(svc.SetInvalid):
        svc.link_to_plan(seeded, 1, 1)


def test_linking_to_a_missing_plan_is_not_found(seeded):
    with pytest.raises(svc.SetNotFound):
        svc.link_to_plan(seeded, 1, 999)


def test_linking_drops_a_stale_comparison(seeded):
    played = svc.get(seeded, 2)
    played.comparison_cache = '{"stale": true}'
    seeded.commit()

    svc.link_to_plan(seeded, 2, 1)

    assert svc.get(seeded, 2).comparison_cache is None


def test_unlink_is_never_an_error_even_when_unlinked(seeded):
    svc.unlink_from_plan(seeded, 1)

    assert svc.get(seeded, 1).planned_set_id is None


def test_compare_without_a_plan_explains_what_to_do(seeded):
    with pytest.raises(svc.SetNotFound, match="link one first"):
        svc.compare(seeded, 1)


def test_cached_analysis_before_analysing_says_so(seeded):
    with pytest.raises(svc.SetNotFound, match="has not been analyzed"):
        svc.cached_analysis(seeded, 1)


def test_cached_comparison_before_comparing_says_so(seeded):
    with pytest.raises(svc.SetNotFound, match="hasn't been compared"):
        svc.cached_comparison(seeded, 1)


# ── replacements ───────────────────────────────────────────────────────


def test_replacement_candidates_exclude_tracks_already_in_the_set(seeded):
    result = svc.replacement_candidates(seeded, 1, position=1)
    in_set = {1, 2, 3}

    for cand, *_ in result["candidates"]:
        assert cand.id not in in_set


def test_replacement_candidates_report_both_neighbours(seeded):
    result = svc.replacement_candidates(seeded, 1, position=1)

    assert result["prev_track"].id == 1
    assert result["next_track"].id == 3


def test_replacement_at_the_edges_has_one_neighbour(seeded):
    first = svc.replacement_candidates(seeded, 1, position=0)
    last = svc.replacement_candidates(seeded, 1, position=2)

    assert first["prev_track"] is None
    assert last["next_track"] is None


def test_replacement_rejects_a_position_outside_the_set(seeded):
    with pytest.raises(svc.SetNotFound, match="Invalid position"):
        svc.replacement_candidates(seeded, 1, position=99)


def test_energy_target_falls_back_when_the_profile_is_unreadable(seeded):
    s = svc.get(seeded, 1)
    s.energy_profile = "not a profile"
    seeded.commit()

    result = svc.replacement_candidates(seeded, 1, position=1)

    assert result["energy_target"] == 0.5
