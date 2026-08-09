"""Keep the test suite away from the real library.

Some code paths reach `kiku.db.models.get_session()`, which brings the *configured*
database to head. That used to be a harmless `create_all` no-op on an existing
schema; now that Alembic owns the schema it is real DDL, so a bare `pytest` run
would migrate whatever `~/.kiku/config.toml` points at — normally the DJ's actual
library.

`pytest_configure` runs before collection, so the override is in place before any
test module can resolve a database path at import time.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_tmpdir: tempfile.TemporaryDirectory | None = None


def pytest_configure(config):
    global _tmpdir
    _tmpdir = tempfile.TemporaryDirectory(prefix="kiku-tests-")
    os.environ["KIKU_DB_PATH"] = str(Path(_tmpdir.name) / "test.db")


def pytest_unconfigure(config):
    global _tmpdir
    if _tmpdir is not None:
        _tmpdir.cleanup()
        _tmpdir = None
