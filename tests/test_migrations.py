"""The migration chain must be able to build the schema from nothing.

Kiku's schema used to be maintained by ``Base.metadata.create_all()``, with Alembic
kept as a decorative parallel record that had silently stopped working — a run from
base raised ``no such table: hunt_tracks``. These tests make "Alembic is the source
of truth" an invariant instead of an intention.
"""

from __future__ import annotations

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import NullPool

from kiku.config import PROJECT_ROOT
from kiku.db.models import Base


@pytest.fixture()
def migrated_engine(tmp_path, monkeypatch):
    """A database built only by running the migration chain from base."""
    db_path = tmp_path / "migrated.db"
    monkeypatch.setenv("KIKU_DB_PATH", str(db_path))

    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path}", poolclass=NullPool)
    yield engine
    engine.dispose()


def test_upgrade_from_base_succeeds(migrated_engine):
    """`alembic upgrade head` runs on an empty database."""
    tables = set(inspect(migrated_engine).get_table_names())
    assert "alembic_version" in tables


def test_every_orm_table_is_created_by_a_migration(migrated_engine):
    """No table may exist in the ORM without a migration that creates it.

    This is the check that would have caught hunt_sessions/hunt_tracks.
    """
    migrated = set(inspect(migrated_engine).get_table_names())
    declared = set(Base.metadata.tables)
    missing = declared - migrated
    assert not missing, (
        f"ORM tables with no migration: {sorted(missing)}. "
        "Add a revision that creates them — do not rely on create_all()."
    )


def test_migrated_schema_matches_the_orm(migrated_engine):
    """The migrated schema and Base.metadata must not have drifted apart."""
    with migrated_engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        diff = compare_metadata(ctx, Base.metadata)

    # SQLite reports no server-side type detail for several of our columns, so
    # type-only differences are noise here. Structural drift is what matters.
    structural = [d for d in diff if not (isinstance(d, tuple) and d and d[0] == "modify_type")]
    assert not structural, (
        "Schema drift between Alembic and the ORM:\n"
        + "\n".join(f"  {d}" for d in structural)
    )
