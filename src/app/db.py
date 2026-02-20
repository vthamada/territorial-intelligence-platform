from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.settings import Settings, get_settings


@lru_cache(maxsize=1)
def get_engine(settings: Settings | None = None):
    settings = settings or get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=600,
        future=True,
    )


@lru_cache(maxsize=1)
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
