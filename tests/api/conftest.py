"""Shared fixtures for API tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.api.deps import get_db
from kiku.api.main import create_app
from kiku.db.models import Base, HuntSession, HuntTrack, Set, SetTrack, Track


@pytest.fixture()
def db_session(tmp_path):
    """Create an in-memory SQLite DB with schema and seed data."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed tracks
    for i in range(1, 21):
        session.add(Track(
            id=i,
            title=f"Track {i}",
            artist=f"Artist {(i % 5) + 1}",
            bpm=120.0 + i,
            key="8A" if i % 2 == 0 else "8B",
            dir_genre="techno" if i <= 10 else "house",
            dir_energy="mid" if i <= 10 else "high",
            duration_sec=300.0 + i * 10,
            rating=3,
            play_count=i,
            kiku_play_count=i % 3,
        ))

    # Seed a set with tracks
    s = Set(id=1, name="Test Set", duration_min=60)
    session.add(s)
    session.flush()
    for pos in range(1, 6):
        session.add(SetTrack(set_id=1, position=pos, track_id=pos, transition_score=0.75))

    # Seed tinder queue: tracks 1-10 have auto predictions at varying confidence
    for i in range(1, 11):
        t = session.get(Track, i)
        t.energy_predicted = "build" if i <= 5 else "peak"
        t.energy_confidence = i * 0.1  # 0.1 to 1.0
        t.energy_source = "auto"

    # Seed a hunt session
    hs = HuntSession(
        id=1, url="https://www.youtube.com/watch?v=test123",
        platform="youtube", title="Test DJ Set", uploader="TestDJ",
        status="complete", track_count=3, owned_count=1,
    )
    session.add(hs)
    session.flush()
    session.add(HuntTrack(
        session_id=1, position=1, artist="Artist 1", title="Track 1",
        confidence=0.9, source="description", acquisition_status="owned",
        matched_track_id=1, match_score=0.95, purchase_links="{}",
    ))
    session.add(HuntTrack(
        session_id=1, position=2, artist="Unknown Artist", title="Mystery Track",
        confidence=0.7, source="description", acquisition_status="unowned",
        purchase_links='{"beatport":"https://www.beatport.com/search?q=test"}',
    ))
    session.add(HuntTrack(
        session_id=1, position=3, artist="Another One", title="Deep Cut",
        confidence=0.6, source="comment", acquisition_status="wanted",
        purchase_links='{"bandcamp":"https://bandcamp.com/search?q=test"}',
    ))

    session.commit()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db_session):
    """TestClient with overridden DB dependency."""
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
