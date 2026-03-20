"""Unit tests for fuzzy library matching."""

from __future__ import annotations

import pytest


@pytest.fixture()
def db_session(tmp_path):
    """Minimal DB session for matcher tests."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    from kiku.db.models import Base, Track

    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    for i in range(1, 6):
        session.add(Track(
            id=i, title=f"Track {i}", artist=f"Artist {i}",
            bpm=125.0, key="8A",
        ))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def test_match_exact(db_session):
    """Exact match against library returns owned status."""
    from kiku.hunting.matcher import match_tracks

    extracted = [{"artist": "Artist 1", "title": "Track 1"}]
    result = match_tracks(db_session, extracted)
    assert result[0]["acquisition_status"] == "owned"
    assert result[0]["matched_track_id"] == 1


def test_match_no_match(db_session):
    """Unknown track returns unowned status."""
    from kiku.hunting.matcher import match_tracks

    extracted = [{"artist": "Completely Unknown", "title": "Nonexistent Song XYZ"}]
    result = match_tracks(db_session, extracted)
    assert result[0]["acquisition_status"] == "unowned"
    assert result[0]["matched_track_id"] is None
