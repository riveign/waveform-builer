"""Shared fixtures for API tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from djsetbuilder.api.deps import get_db
from djsetbuilder.api.main import create_app
from djsetbuilder.db.models import Base, Set, SetTrack, Track


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
        ))

    # Seed a set with tracks
    s = Set(id=1, name="Test Set", duration_min=60)
    session.add(s)
    session.flush()
    for pos in range(1, 6):
        session.add(SetTrack(set_id=1, position=pos, track_id=pos, transition_score=0.75))

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
