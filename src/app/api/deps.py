from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db import get_session_factory


def get_db() -> Generator[Session, None, None]:
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
