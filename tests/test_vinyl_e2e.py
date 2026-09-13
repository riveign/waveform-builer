"""End to end: a record on the shelf becomes a row the builder can reach.

Runs against a database built by the real migration chain, not `create_all`, so
the columns under test are the ones a DJ's library will actually get.

The Discogs payload is the shape of a real response, checked against the live API
on 2026-09-10 (Alarico — Klockworks 38, release 28715971): empty durations and
all, because that is what a 12" actually returns.
"""

from __future__ import annotations

import httpx
import pytest
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from alembic import command
from kiku.config import PROJECT_ROOT
from kiku.db.models import Track, VinylRelease
from kiku.metadata.sources.discogs import DiscogsSource
from kiku.setbuilder.planner import _get_candidate_pool
from kiku.vinyl.importer import apply_import, set_manual_bpm_key

RELEASE_JSON = {
    "id": 28715971,
    "title": "Klockworks 38",
    "year": 2023,
    "country": "Germany",
    "uri": "https://www.discogs.com/release/28715971",
    "artists": [{"name": "Alarico (2)", "join": ""}],
    "labels": [{"name": "Klockworks", "catno": "KW 38"}],
    "formats": [{"name": "Vinyl", "qty": "1", "descriptions": ['12"']}],
    "images": [{"uri": "https://i.discogs.com/x.jpg"}],
    "tracklist": [
        {"type_": "heading", "position": "", "title": "Side A"},
        {"type_": "track", "position": "A1", "title": "AF 97", "duration": ""},
        {"type_": "track", "position": "A2", "title": "Chromo", "duration": ""},
        {"type_": "track", "position": "B1", "title": "Lost In Lima", "duration": ""},
        {"type_": "track", "position": "B2", "title": "Nisba", "duration": ""},
        {"type_": "track", "position": "Digi 1", "title": "AF 97 (Edit)", "duration": "4:02"},
    ],
}


@pytest.fixture()
def migrated_session(tmp_path, monkeypatch):
    db_path = tmp_path / "e2e.db"
    monkeypatch.setenv("KIKU_DB_PATH", str(db_path))
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path}", poolclass=NullPool)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()
    engine.dispose()


@pytest.fixture()
def discogs() -> DiscogsSource:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/releases/28715971":
            return httpx.Response(200, json=RELEASE_JSON)
        if request.url.path == "/database/search":
            return httpx.Response(200, json={"results": [{"id": 28715971}]})
        return httpx.Response(404, json={})

    return DiscogsSource(token="test-token", transport=httpx.MockTransport(handler))


def test_shelf_to_set(migrated_session, discogs):
    session = migrated_session

    # 1. Look the record up.
    candidates = discogs.search("Klockworks 38", "Alarico", limit=1)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.catalog_number == "KW 38"
    assert candidate.artist == "Alarico"  # the "(2)" disambiguator is stripped
    # The heading row is not a track; the download-only bonus is.
    assert [r.position_raw for r in candidate.recordings] == ["A1", "A2", "B1", "B2", "Digi 1"]

    # 2. It lands on the shelf, flagged, with nothing invented.
    release = apply_import(session, candidate, acquired_on="2026-09-10")
    assert session.query(VinylRelease).count() == 1
    assert release.rpm is None  # this pressing doesn't say — NULL, not a guess
    assert release.side_count == 2  # A and B — "Digi 1" is not a side

    rows = session.query(Track).filter(Track.medium == "vinyl").all()
    assert len(rows) == 5
    assert all(t.bpm is None and t.enrichment_status == "pending" for t in rows)
    # Discogs carried a duration for exactly one of them.
    assert sum(1 for t in rows if t.duration_sec) == 1

    # 3. Before a BPM exists, the builder cannot reach it — and neither can an
    #    opt-in build, because there is nothing to plan with.
    assert _get_candidate_pool(session, include_vinyl=True) == []

    # 4. The DJ types the number. That is the import path (Research R2).
    a1 = session.query(Track).filter_by(vinyl_position="A1").one()
    set_manual_bpm_key(session, a1.id, bpm=136.0, key="8A")

    # 5. Now it is a first-class candidate — but only when asked for (Risk 3).
    assert _get_candidate_pool(session) == []
    pool = _get_candidate_pool(session, include_vinyl=True)
    assert [t.vinyl_position for t in pool] == ["A1"]
    assert pool[0].bpm_source == "manual"

    # 6. Adding the same pressing again doesn't grow a second shelf, and doesn't
    #    forget what was typed.
    apply_import(session, candidate)
    assert session.query(VinylRelease).count() == 1
    assert session.query(Track).filter(Track.medium == "vinyl").count() == 5
    session.refresh(a1)
    assert a1.bpm == 136.0


def test_existing_digital_library_is_untouched_by_the_migration(migrated_session):
    """Every row that existed before spec 030 reads as digital, and still plans."""
    session = migrated_session
    session.add(
        Track(
            title="A file",
            artist="Someone",
            bpm=134.0,
            key="8A",
            file_path="/run/media/mantis/SSD/Musica/a.aiff",
        )
    )
    session.commit()

    row = session.query(Track).one()
    assert row.medium is None or row.medium == "digital"
    assert len(_get_candidate_pool(session)) == 1
