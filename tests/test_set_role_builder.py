"""Spec 028 — set roles shaping the auto-builder (soft bias) + teaching."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.db.models import Base, Set, SetTrack, Track
from kiku.set_roles import has_role, track_roles
from kiku.setbuilder.constraints import parse_energy_string
from kiku.setbuilder.planner import _pick_seed


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _t(session, tid, energy, roles=None, bpm=124.0, key="8A"):
    tr = Track(id=tid, title=f"T{tid}", artist=f"A{tid}", bpm=bpm, key=key,
               dir_energy=energy, set_roles=json.dumps(roles) if roles else None)
    session.add(tr)
    return tr


def test_track_roles_parse(session):
    tr = _t(session, 1, "warmup", roles=["opener", "bogus"])
    assert track_roles(tr) == ["opener"]           # unknown dropped
    assert has_role(tr, "opener") and not has_role(tr, "closer")
    assert track_roles(_t(session, 2, "warmup")) == []  # untagged


def test_seed_prefers_opener_when_energy_close(session):
    prof = parse_energy_string("warmup:30:0.3,peak:30:0.9")
    # both near the 0.3 warmup target; #2 is the marked opener
    a = _t(session, 1, "warmup")                    # ~low energy, no role
    b = _t(session, 2, "warmup", roles=["opener"])  # ~low energy, opener
    session.commit()
    assert _pick_seed([a, b], prof).id == 2


def test_seed_does_not_force_opener_on_clear_loss(session):
    prof = parse_energy_string("warmup:30:0.3,peak:30:0.9")
    # #1 sits ON the warmup target; #2 is a peak-energy opener (far from target)
    a = _t(session, 1, "warmup")                    # great energy fit, no role
    b = _t(session, 2, "peak", roles=["opener"])    # opener but wrong energy
    session.commit()
    # the ~0.15 bonus must NOT overcome a large energy gap
    assert _pick_seed([a, b], prof).id == 1


def test_teaching_notes_for_tagged_first_and_last(session):
    from kiku.analysis.set_analyzer import analyze_set
    o = _t(session, 1, "warmup", roles=["opener"])
    m = _t(session, 2, "build")
    c = _t(session, 3, "close", roles=["closer"])
    st = Set(id=1, name="S", duration_min=30)
    session.add(st)
    session.flush()
    for pos, tr in enumerate([o, m, c]):
        session.add(SetTrack(set_id=1, position=pos, track_id=tr.id))
    session.commit()
    res = analyze_set(session, 1)
    joined = " ".join(res.set_patterns)
    assert "great opener" in joined and "go-to closers" in joined
