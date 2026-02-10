from __future__ import annotations

import json

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

    assert command[0] == "dbt"
    assert command[1] == "run"
    assert "--project-dir" in command
    assert "--profiles-dir" in command
    assert "--profile" in command
    assert "--target" in command
    assert command[-2] == "--vars"
    payload = json.loads(command[-1])
    assert payload["reference_period"] == "2024"
