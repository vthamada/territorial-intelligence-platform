from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


def _load_module():
    module_path = Path("scripts/run_incremental_backfill.py")
    spec = importlib.util.spec_from_file_location("run_incremental_backfill", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_csv_values_trims_and_removes_empty_tokens() -> None:
    module = _load_module()

    values = module._parse_csv_values(" 2025, ,2024 ,, 2023 ")

    assert values == ["2025", "2024", "2023"]


def test_decide_incremental_action_executes_without_previous_run() -> None:
    module = _load_module()
    now_utc = datetime.now(tz=UTC)

    decision = module._decide_incremental_action(
        job_name="sidra_indicators_fetch",
        reference_period="2025",
        latest_status=None,
        latest_started_at_utc=None,
        now_utc=now_utc,
        stale_after_hours=24,
        reprocess_jobs=set(),
        reprocess_periods=set(),
    )

    assert decision["execute"] is True
    assert decision["reason"] == "no_previous_run"


def test_decide_incremental_action_skips_fresh_success() -> None:
    module = _load_module()
    now_utc = datetime.now(tz=UTC)

    decision = module._decide_incremental_action(
        job_name="sidra_indicators_fetch",
        reference_period="2025",
        latest_status="success",
        latest_started_at_utc=now_utc - timedelta(hours=2),
        now_utc=now_utc,
        stale_after_hours=24,
        reprocess_jobs=set(),
        reprocess_periods=set(),
    )

    assert decision["execute"] is False
    assert decision["reason"] == "fresh_success_lt_24h"
    assert decision["age_hours"] == 2.0


def test_decide_incremental_action_executes_stale_success() -> None:
    module = _load_module()
    now_utc = datetime.now(tz=UTC)

    decision = module._decide_incremental_action(
        job_name="sidra_indicators_fetch",
        reference_period="2025",
        latest_status="success",
        latest_started_at_utc=now_utc - timedelta(hours=30),
        now_utc=now_utc,
        stale_after_hours=24,
        reprocess_jobs=set(),
        reprocess_periods=set(),
    )

    assert decision["execute"] is True
    assert decision["reason"] == "stale_success_ge_24h"
    assert decision["age_hours"] == 30.0


def test_decide_incremental_action_executes_when_latest_status_is_not_success() -> None:
    module = _load_module()
    now_utc = datetime.now(tz=UTC)

    decision = module._decide_incremental_action(
        job_name="sidra_indicators_fetch",
        reference_period="2025",
        latest_status="failed",
        latest_started_at_utc=now_utc - timedelta(hours=1),
        now_utc=now_utc,
        stale_after_hours=24,
        reprocess_jobs=set(),
        reprocess_periods=set(),
    )

    assert decision["execute"] is True
    assert decision["reason"] == "latest_status_failed"
    assert decision["age_hours"] is None


def test_decide_incremental_action_reprocess_selector_overrides_fresh_success() -> None:
    module = _load_module()
    now_utc = datetime.now(tz=UTC)

    decision = module._decide_incremental_action(
        job_name="sidra_indicators_fetch",
        reference_period="2025",
        latest_status="success",
        latest_started_at_utc=now_utc - timedelta(hours=1),
        now_utc=now_utc,
        stale_after_hours=24,
        reprocess_jobs={"sidra_indicators_fetch"},
        reprocess_periods=set(),
    )

    assert decision["execute"] is True
    assert decision["reason"] == "reprocess_selected"
