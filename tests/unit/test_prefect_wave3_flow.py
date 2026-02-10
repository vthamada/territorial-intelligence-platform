from __future__ import annotations

from typing import Any

from orchestration import prefect_flows


def test_run_mvp_wave_3_propagates_common_kwargs_to_all_jobs(monkeypatch) -> None:
    calls: dict[str, dict[str, Any]] = {}

    def _stub(job_name: str):
        def _run(**kwargs: Any) -> dict[str, Any]:
            calls[job_name] = kwargs
            return {"job": job_name, "status": "success", "rows_written": 1}

        return _run

    monkeypatch.setattr(prefect_flows, "run_inep_education", _stub("education_inep_fetch"))
    monkeypatch.setattr(prefect_flows, "run_datasus_health", _stub("health_datasus_fetch"))
    monkeypatch.setattr(prefect_flows, "run_siconfi_finance", _stub("finance_siconfi_fetch"))
    monkeypatch.setattr(prefect_flows, "run_mte_labor", _stub("labor_mte_fetch"))
    monkeypatch.setattr(prefect_flows, "run_quality_suite", _stub("quality_suite"))

    result = prefect_flows.run_mvp_wave_3.fn(
        reference_period="2024",
        force=True,
        dry_run=False,
        max_retries=5,
        timeout_seconds=45,
    )

    assert set(result.keys()) == {
        "education_inep_fetch",
        "health_datasus_fetch",
        "finance_siconfi_fetch",
        "labor_mte_fetch",
        "quality_suite",
    }
    expected_kwargs = {
        "reference_period": "2024",
        "force": True,
        "dry_run": False,
        "max_retries": 5,
        "timeout_seconds": 45,
    }
    assert calls["education_inep_fetch"] == expected_kwargs
    assert calls["health_datasus_fetch"] == expected_kwargs
    assert calls["finance_siconfi_fetch"] == expected_kwargs
    assert calls["labor_mte_fetch"] == expected_kwargs
    assert calls["quality_suite"] == expected_kwargs


def test_run_mvp_wave_3_returns_each_job_result_payload(monkeypatch) -> None:
    def _run_inep(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "education_inep_fetch", "status": "success", "rows_written": 1}

    def _run_datasus(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "health_datasus_fetch", "status": "success", "rows_written": 2}

    def _run_siconfi(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "finance_siconfi_fetch", "status": "success", "rows_written": 3}

    def _run_mte(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "labor_mte_fetch", "status": "blocked", "rows_written": 0}

    def _run_quality(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "quality_suite", "status": "success", "results": []}

    monkeypatch.setattr(prefect_flows, "run_inep_education", _run_inep)
    monkeypatch.setattr(prefect_flows, "run_datasus_health", _run_datasus)
    monkeypatch.setattr(prefect_flows, "run_siconfi_finance", _run_siconfi)
    monkeypatch.setattr(prefect_flows, "run_mte_labor", _run_mte)
    monkeypatch.setattr(prefect_flows, "run_quality_suite", _run_quality)

    result = prefect_flows.run_mvp_wave_3.fn(
        reference_period="2024",
        dry_run=True,
    )

    assert result["education_inep_fetch"]["rows_written"] == 1
    assert result["health_datasus_fetch"]["rows_written"] == 2
    assert result["finance_siconfi_fetch"]["rows_written"] == 3
    assert result["labor_mte_fetch"]["status"] == "blocked"
    assert result["quality_suite"]["job"] == "quality_suite"
