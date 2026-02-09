from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.settings import Settings, get_settings


def get_engine(settings: Settings | None = None):
    settings = settings or get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


def get_session_factory(settings: Settings | None = None):
    engine = get_engine(settings)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


@contextmanager
def session_scope(settings: Settings | None = None) -> Iterator[Session]:
    factory = get_session_factory(settings)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def healthcheck(settings: Settings | None = None) -> bool:
    engine = get_engine(settings)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
