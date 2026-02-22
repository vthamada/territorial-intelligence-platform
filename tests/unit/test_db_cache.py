from __future__ import annotations

import pytest

from app import db as db_module
from app.settings import Settings


def _build_settings(database_url: str) -> Settings:
    return Settings(
        municipality_ibge_code="3121605",
        database_url=database_url,
    )


@pytest.fixture(autouse=True)
def _clear_db_caches() -> None:
    db_module._get_engine_cached.cache_clear()
    db_module._get_session_factory_cached.cache_clear()


def test_get_engine_caches_by_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def _fake_create_engine(database_url: str, **kwargs):  # noqa: ANN001, ARG001
        calls.append(database_url)
        return {"database_url": database_url}

    monkeypatch.setattr(db_module, "create_engine", _fake_create_engine)
    settings = _build_settings("postgresql+psycopg://postgres:postgres@localhost:5432/test_db")

    engine_first = db_module.get_engine(settings)
    engine_second = db_module.get_engine(settings)

    assert engine_first is engine_second
    assert calls == ["postgresql+psycopg://postgres:postgres@localhost:5432/test_db"]


def test_get_session_factory_accepts_settings_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    engine_calls: list[str] = []
    sessionmaker_calls: list[object] = []

    def _fake_create_engine(database_url: str, **kwargs):  # noqa: ANN001, ARG001
        engine_calls.append(database_url)
        return {"database_url": database_url}

    def _fake_sessionmaker(**kwargs):  # noqa: ANN001
        sessionmaker_calls.append(kwargs["bind"])
        return lambda: None

    monkeypatch.setattr(db_module, "create_engine", _fake_create_engine)
    monkeypatch.setattr(db_module, "sessionmaker", _fake_sessionmaker)
    settings = _build_settings("postgresql+psycopg://postgres:postgres@localhost:5432/another_db")

    factory_first = db_module.get_session_factory(settings)
    factory_second = db_module.get_session_factory(settings)

    assert factory_first is factory_second
    assert engine_calls == ["postgresql+psycopg://postgres:postgres@localhost:5432/another_db"]
    assert len(sessionmaker_calls) == 1
