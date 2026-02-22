from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

from pipelines.common.quality import CheckResult
from pipelines import quality_suite


def test_quality_suite_includes_map_layer_checks(monkeypatch: Any) -> None:
    fake_session = object()
    captured: dict[str, Any] = {}
    called = {"map_layers": False}

    @contextmanager
    def _session_scope(_settings: Any):
        yield fake_session

    def _empty_checks(*_args: Any, **_kwargs: Any) -> list[CheckResult]:
        return []

    def _map_layer_checks(*_args: Any, **_kwargs: Any) -> list[CheckResult]:
        called["map_layers"] = True
        return [
            CheckResult(
                name="map_layer_rows_municipality",
                status="pass",
                details="Map layer rows check.",
                observed_value=1,
                threshold_value=1,
            )
        ]

    def _upsert_pipeline_run(**kwargs: Any) -> None:
        captured["run_status"] = kwargs["status"]

    def _replace_pipeline_checks(*, checks: list[CheckResult], **_kwargs: Any) -> None:
        captured["check_names"] = [check.name for check in checks]

    monkeypatch.setattr(quality_suite, "get_settings", lambda: SimpleNamespace(municipality_ibge_code="3121605"))
    monkeypatch.setattr(quality_suite, "load_quality_thresholds", lambda: object())
    monkeypatch.setattr(quality_suite, "session_scope", _session_scope)
    monkeypatch.setattr(quality_suite, "upsert_pipeline_run", _upsert_pipeline_run)
    monkeypatch.setattr(quality_suite, "replace_pipeline_checks", _replace_pipeline_checks)
    monkeypatch.setattr(quality_suite, "check_dim_territory", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_dim_territory_electoral_zone_integrity", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_map_layers", _map_layer_checks)
    monkeypatch.setattr(quality_suite, "check_fact_electorate", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_fact_electorate_temporal_coverage", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_fact_election_result", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_fact_election_result_temporal_coverage", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_fact_indicator", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_fact_indicator_temporal_coverage", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_fact_indicator_source_rows", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_fact_indicator_source_temporal_coverage", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_fact_social_protection", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_fact_social_assistance_network", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_urban_domain", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_environment_risk_aggregation", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_environment_risk_mart", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_source_schema_contracts", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_source_schema_drift", _empty_checks)
    monkeypatch.setattr(quality_suite, "check_ops_pipeline_runs", _empty_checks)

    result = quality_suite.run(reference_period="2025")

    assert called["map_layers"] is True
    assert result["status"] == "success"
    assert result["results"] == [
        {
            "name": "map_layer_rows_municipality",
            "status": "pass",
            "details": "Map layer rows check.",
            "observed_value": 1,
            "threshold_value": 1,
        }
    ]
    assert captured["run_status"] == "success"
    assert captured["check_names"] == ["map_layer_rows_municipality"]
