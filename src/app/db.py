from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.settings import Settings, get_settings


def _resolve_database_url(settings: Settings | None = None) -> str:
    resolved_settings = settings or get_settings()
    return str(resolved_settings.database_url)


@lru_cache(maxsize=4)
def _get_engine_cached(database_url: str):
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=600,
        future=True,
    )


def get_engine(settings: Settings | None = None):
    return _get_engine_cached(_resolve_database_url(settings))


@lru_cache(maxsize=4)
def _get_session_factory_cached(database_url: str):
    engine = _get_engine_cached(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def get_session_factory(settings: Settings | None = None):
    return _get_session_factory_cached(_resolve_database_url(settings))


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
