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
            "sidra_indicators_fetch": 1,
            "senatran_fleet_fetch": 1,
            "sejusp_public_safety_fetch": 1,
            "siops_health_finance_fetch": 1,
            "snis_sanitation_fetch": 1,
            "inmet_climate_fetch": 1,
            "inpe_queimadas_fetch": 1,
            "ana_hydrology_fetch": 1,
            "anatel_connectivity_fetch": 1,
            "aneel_energy_fetch": 1,
            "urban_roads_fetch": 1,
            "urban_pois_fetch": 1,
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
    assert by_name["mvp4_pipeline_run_sidra_indicators_fetch"].status == "pass"
    assert by_name["mvp4_pipeline_run_senatran_fleet_fetch"].status == "pass"
    assert by_name["mvp4_pipeline_run_sejusp_public_safety_fetch"].status == "pass"
    assert by_name["mvp4_pipeline_run_siops_health_finance_fetch"].status == "pass"
    assert by_name["mvp4_pipeline_run_snis_sanitation_fetch"].status == "pass"
    assert by_name["mvp5_pipeline_run_inmet_climate_fetch"].status == "pass"
    assert by_name["mvp5_pipeline_run_inpe_queimadas_fetch"].status == "pass"
    assert by_name["mvp5_pipeline_run_ana_hydrology_fetch"].status == "pass"
    assert by_name["mvp5_pipeline_run_anatel_connectivity_fetch"].status == "pass"
    assert by_name["mvp5_pipeline_run_aneel_energy_fetch"].status == "pass"
    assert by_name["mvp7_pipeline_run_urban_roads_fetch"].status == "pass"
    assert by_name["mvp7_pipeline_run_urban_pois_fetch"].status == "pass"
