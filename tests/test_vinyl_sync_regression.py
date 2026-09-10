"""`kiku sync` must never touch a record on the shelf.

This is the one silent-data-loss risk in spec 030 (Human Section L20).
Reconciliation matches on `rb_id` then normalized `file_path` — a vinyl row has
neither, so it should be invisible to sync. Nothing enforces that today except
the shape of two queries, which is exactly why it is pinned here: a future
"clean up orphans" pass would eat the crate without a single failing test.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.db.models import Base, Track
from kiku.db.sync import _backfill_filename_track_numbers


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 's.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture()
def shelf(session):
    session.add(
        Track(
            medium="vinyl",
            title="AF 97",
            artist="Alarico",
            album="Klockworks 38",
            vinyl_position="A1",
            disc_number=1,
            track_number=1,
            bpm=136.0,
            bpm_source="manual",
            enrichment_status="manual",
        )
    )
    session.commit()
    return session.query(Track).filter_by(medium="vinyl").one()


def test_a_vinyl_row_is_unreachable_by_rb_id_match(session, shelf):
    """Sync's first lookup is `filter_by(rb_id=...)`. Vinyl has no rb_id."""
    assert shelf.rb_id is None
    assert session.query(Track).filter_by(rb_id="12345").first() is None


def test_a_vinyl_row_is_unreachable_by_file_path_match(session, shelf):
    """Sync's fallback is `filter_by(file_path=...)`. Vinyl has no path.

    A NULL file_path must never be matched by a path lookup — if it were, the
    first Rekordbox track with an empty FolderPath would overwrite a record.
    """
    assert shelf.file_path is None
    assert session.query(Track).filter_by(file_path="").first() is None
    assert session.query(Track).filter_by(file_path="/Volumes/SSD/x.aiff").first() is None


def test_the_track_number_backfill_cannot_scramble_a_side(session, shelf):
    """`_backfill_filename_track_numbers` only touches rows with a file_path."""
    shelf.track_number = None
    session.commit()

    _backfill_filename_track_numbers(session)

    session.refresh(shelf)
    assert shelf.track_number is None  # untouched — it has no filename to read
    assert shelf.vinyl_position == "A1"


def test_sync_never_deletes(session, shelf):
    """Reconciliation adds and updates; it has no delete path. Pin that."""
    import inspect

    from kiku.db import sync as sync_mod

    source = inspect.getsource(sync_mod)
    assert ".delete()" not in source, (
        "sync.py grew a delete path — a vinyl row has no rb_id and no file_path, "
        "so any 'remove what Rekordbox no longer has' pass would eat the shelf."
    )
