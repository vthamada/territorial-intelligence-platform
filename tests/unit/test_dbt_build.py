from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from pipelines import dbt_build
from pipelines.dbt_build import _load_gold_models


def test_load_gold_models_finds_mart_indicator_latest() -> None:
    models = _load_gold_models()
    names = [name for name, _ in models]
    assert "mart_indicator_latest" in names


def test_resolve_requested_build_mode_defaults_to_auto(monkeypatch) -> None:
    monkeypatch.delenv("DBT_BUILD_MODE", raising=False)
    assert dbt_build._resolve_requested_build_mode() == "auto"


def test_resolve_requested_build_mode_rejects_invalid_value(monkeypatch) -> None:
    monkeypatch.setenv("DBT_BUILD_MODE", "invalid")
    with pytest.raises(RuntimeError, match="Invalid DBT_BUILD_MODE"):
        dbt_build._resolve_requested_build_mode()


def test_decide_effective_build_mode_in_auto(monkeypatch) -> None:
    del monkeypatch
    assert dbt_build._decide_effective_build_mode("auto", dbt_available=False) == "sql_direct"
    assert dbt_build._decide_effective_build_mode("auto", dbt_available=True) == "dbt_cli"


def test_decide_effective_build_mode_requires_dbt_cli_when_forced(monkeypatch) -> None:
    del monkeypatch
    with pytest.raises(RuntimeError, match="dbt CLI is not available"):
        dbt_build._decide_effective_build_mode("dbt", dbt_available=False)


def test_build_dbt_run_command_includes_reference_period_and_profile_settings(monkeypatch) -> None:
    monkeypatch.setenv("DBT_PROFILES_DIR", "C:/tmp/.dbt")
    monkeypatch.setenv("DBT_PROFILE", "territorial_intelligence")
    monkeypatch.setenv("DBT_TARGET", "dev")

    command = dbt_build._build_dbt_run_command(reference_period="2024")

    assert Path(command[0]).name in {"dbt", "dbt.exe"}
    assert command[1] == "run"
    assert "--project-dir" in command
    assert "--profiles-dir" in command
    assert "--profile" in command
    assert "--target" in command
    assert command[-2] == "--vars"
    payload = json.loads(command[-1])
    assert payload["reference_period"] == "2024"


def test_resolve_dbt_executable_uses_venv_scripts_when_not_on_path(monkeypatch) -> None:
    fake_scripts = Path("tmp") / "test_dbt_executable" / "Scripts"
    if fake_scripts.parent.exists():
        shutil.rmtree(fake_scripts.parent, ignore_errors=True)
    fake_scripts.mkdir(parents=True, exist_ok=True)
    fake_dbt = fake_scripts / "dbt.exe"
    fake_dbt.write_text("", encoding="utf-8")

    monkeypatch.setattr(dbt_build.shutil, "which", lambda _name: None)
    monkeypatch.setattr(dbt_build.sys, "executable", str(fake_scripts / "python.exe"))

    resolved = dbt_build._resolve_dbt_executable()

    assert resolved is not None
    assert Path(resolved).name.lower() == "dbt.exe"

    shutil.rmtree(fake_scripts.parent, ignore_errors=True)


def test_run_persists_failed_check_when_execution_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        dbt_build,
        "_load_gold_models",
        lambda: [("mart_indicator_latest", "SELECT 1 AS value")],
    )
    monkeypatch.setattr(dbt_build, "_resolve_requested_build_mode", lambda: "dbt")
    monkeypatch.setattr(dbt_build, "_dbt_cli_available", lambda: False)

    class _DummyLogger:
        def info(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def exception(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    monkeypatch.setattr(dbt_build, "get_logger", lambda _name: _DummyLogger())

    class _DummySession:
        pass

    class _SessionScope:
        def __enter__(self) -> _DummySession:
            return _DummySession()

        def __exit__(self, _exc_type, _exc, _tb) -> bool:
            return False

    monkeypatch.setattr(dbt_build, "session_scope", lambda _settings: _SessionScope())

    run_calls: list[dict[str, Any]] = []
    check_calls: list[dict[str, Any]] = []

    monkeypatch.setattr(
        dbt_build,
        "upsert_pipeline_run",
        lambda **kwargs: run_calls.append(kwargs),
    )
    monkeypatch.setattr(
        dbt_build,
        "replace_pipeline_checks_from_dicts",
        lambda **kwargs: check_calls.append(kwargs),
    )

    result = dbt_build.run(
        reference_period="2025",
        dry_run=False,
        settings=object(),
    )

    assert result["status"] == "failed"
    assert run_calls
    assert run_calls[0]["status"] == "failed"

    assert check_calls
    checks = check_calls[0]["checks"]
    assert checks
    assert checks[0]["name"] == "dbt_build_execution"
    assert checks[0]["status"] == "fail"
