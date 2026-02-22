from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    module_path = Path("scripts/backfill_environment_history.py")
    spec = importlib.util.spec_from_file_location("backfill_environment_history", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_periods_normalizes_and_sorts_years() -> None:
    module = _load_module()

    periods = module._parse_periods("2025, 2023,invalid,2024,2023,20,2022")

    assert periods == ["2022", "2023", "2024", "2025"]


def test_summarize_status_groups_items_by_status() -> None:
    module = _load_module()
    payload = [
        {"status": "success"},
        {"status": "success"},
        {"status": "blocked"},
        {"status": "failed"},
    ]

    summary = module._summarize_status(payload)

    assert summary == {"success": 2, "blocked": 1, "failed": 1}
