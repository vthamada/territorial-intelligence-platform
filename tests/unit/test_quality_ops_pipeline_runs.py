from __future__ import annotations

from typing import Any

from pipelines.common.quality import check_ops_pipeline_runs
from pipelines.common.quality_thresholds import QualityThresholds


class _ScalarResult:
    def __init__(self, value: int) -> None:
        self._value = value

    def scalar_one(self) -> int:
        return self._value


class _FakeSession:
    def __init__(self, counts_by_job: dict[str, int]) -> None:
        self._counts_by_job = counts_by_job

    def execute(self, _statement: Any, params: dict[str, Any]) -> _ScalarResult:
        job_name = str(params["job_name"])
        return _ScalarResult(self._counts_by_job.get(job_name, 0))


def test_check_ops_pipeline_runs_marks_warn_when_job_has_no_successful_run() -> None:
    session = _FakeSession(
        {
            "education_inep_fetch": 1,
            "health_datasus_fetch": 1,
            "finance_siconfi_fetch": 0,
            "labor_mte_fetch": 1,
        }
    )
    thresholds = QualityThresholds(
        defaults={},
        by_table={"ops_pipeline_runs": {"min_successful_runs_per_job": 1}},
    )

    results = check_ops_pipeline_runs(
        session=session,
        reference_period="2024",
        thresholds=thresholds,
    )

    by_name = {result.name: result for result in results}
    assert by_name["mvp3_pipeline_run_finance_siconfi_fetch"].status == "warn"
    assert by_name["mvp3_pipeline_run_education_inep_fetch"].status == "pass"
    assert by_name["mvp3_pipeline_run_labor_mte_fetch"].status == "pass"
