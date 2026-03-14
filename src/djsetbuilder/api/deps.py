"""FastAPI dependencies for DB session management."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from djsetbuilder.db.models import get_session


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and close it after the request."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()
