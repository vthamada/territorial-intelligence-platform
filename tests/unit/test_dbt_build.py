from __future__ import annotations

from pipelines.dbt_build import _load_gold_models


def test_load_gold_models_finds_mart_indicator_latest() -> None:
    models = _load_gold_models()
    names = [name for name, _ in models]
    assert "mart_indicator_latest" in names
