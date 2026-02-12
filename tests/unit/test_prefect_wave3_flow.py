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


def test_run_mvp_all_propagates_common_kwargs_to_all_jobs(monkeypatch) -> None:
    calls: dict[str, dict[str, Any]] = {}

    def _stub(job_name: str):
        def _run(**kwargs: Any) -> dict[str, Any]:
            calls[job_name] = kwargs
            return {"job": job_name, "status": "success", "rows_written": 1}

        return _run

    monkeypatch.setattr(prefect_flows, "run_ibge_admin", _stub("ibge_admin_fetch"))
    monkeypatch.setattr(prefect_flows, "run_ibge_geometries", _stub("ibge_geometries_fetch"))
    monkeypatch.setattr(prefect_flows, "run_ibge_indicators", _stub("ibge_indicators_fetch"))
    monkeypatch.setattr(prefect_flows, "run_tse_catalog", _stub("tse_catalog_discovery"))
    monkeypatch.setattr(prefect_flows, "run_tse_electorate", _stub("tse_electorate_fetch"))
    monkeypatch.setattr(prefect_flows, "run_tse_results", _stub("tse_results_fetch"))
    monkeypatch.setattr(prefect_flows, "run_inep_education", _stub("education_inep_fetch"))
    monkeypatch.setattr(prefect_flows, "run_datasus_health", _stub("health_datasus_fetch"))
    monkeypatch.setattr(prefect_flows, "run_siconfi_finance", _stub("finance_siconfi_fetch"))
    monkeypatch.setattr(prefect_flows, "run_mte_labor", _stub("labor_mte_fetch"))
    monkeypatch.setattr(prefect_flows, "run_sidra_indicators", _stub("sidra_indicators_fetch"))
    monkeypatch.setattr(prefect_flows, "run_senatran_fleet", _stub("senatran_fleet_fetch"))
    monkeypatch.setattr(
        prefect_flows,
        "run_sejusp_public_safety",
        _stub("sejusp_public_safety_fetch"),
    )
    monkeypatch.setattr(
        prefect_flows,
        "run_siops_health_finance",
        _stub("siops_health_finance_fetch"),
    )
    monkeypatch.setattr(prefect_flows, "run_snis_sanitation", _stub("snis_sanitation_fetch"))
    monkeypatch.setattr(prefect_flows, "run_inmet_climate", _stub("inmet_climate_fetch"))
    monkeypatch.setattr(prefect_flows, "run_inpe_queimadas", _stub("inpe_queimadas_fetch"))
    monkeypatch.setattr(prefect_flows, "run_ana_hydrology", _stub("ana_hydrology_fetch"))
    monkeypatch.setattr(prefect_flows, "run_anatel_connectivity", _stub("anatel_connectivity_fetch"))
    monkeypatch.setattr(prefect_flows, "run_aneel_energy", _stub("aneel_energy_fetch"))
    monkeypatch.setattr(prefect_flows, "run_dbt_build", _stub("dbt_build"))
    monkeypatch.setattr(prefect_flows, "run_quality_suite", _stub("quality_suite"))

    result = prefect_flows.run_mvp_all.fn(
        reference_period="2024",
        force=True,
        dry_run=False,
        max_retries=7,
        timeout_seconds=90,
    )

    assert set(result.keys()) == {
        "ibge_admin_fetch",
        "ibge_geometries_fetch",
        "ibge_indicators_fetch",
        "tse_catalog_discovery",
        "tse_electorate_fetch",
        "tse_results_fetch",
        "education_inep_fetch",
        "health_datasus_fetch",
        "finance_siconfi_fetch",
        "labor_mte_fetch",
        "sidra_indicators_fetch",
        "senatran_fleet_fetch",
        "sejusp_public_safety_fetch",
        "siops_health_finance_fetch",
        "snis_sanitation_fetch",
        "inmet_climate_fetch",
        "inpe_queimadas_fetch",
        "ana_hydrology_fetch",
        "anatel_connectivity_fetch",
        "aneel_energy_fetch",
        "dbt_build",
        "quality_suite",
    }
    expected_kwargs = {
        "reference_period": "2024",
        "force": True,
        "dry_run": False,
        "max_retries": 7,
        "timeout_seconds": 90,
    }
    for job_name in result:
        assert calls[job_name] == expected_kwargs


def test_run_mvp_all_returns_each_job_result_payload(monkeypatch) -> None:
    def _run_ibge_admin(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "ibge_admin_fetch", "status": "success", "rows_written": 1}

    def _run_ibge_geometries(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "ibge_geometries_fetch", "status": "success", "rows_written": 2}

    def _run_ibge_indicators(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "ibge_indicators_fetch", "status": "success", "rows_written": 3}

    def _run_tse_catalog(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "tse_catalog_discovery", "status": "success", "rows_written": 4}

    def _run_tse_electorate(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "tse_electorate_fetch", "status": "success", "rows_written": 5}

    def _run_tse_results(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "tse_results_fetch", "status": "success", "rows_written": 6}

    def _run_inep(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "education_inep_fetch", "status": "success", "rows_written": 7}

    def _run_datasus(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "health_datasus_fetch", "status": "success", "rows_written": 8}

    def _run_siconfi(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "finance_siconfi_fetch", "status": "success", "rows_written": 9}

    def _run_mte(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "labor_mte_fetch", "status": "blocked", "rows_written": 0}

    def _run_dbt(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "dbt_build", "status": "success", "models_built": 3}

    def _run_quality(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "quality_suite", "status": "success", "results": []}

    monkeypatch.setattr(prefect_flows, "run_ibge_admin", _run_ibge_admin)
    monkeypatch.setattr(prefect_flows, "run_ibge_geometries", _run_ibge_geometries)
    monkeypatch.setattr(prefect_flows, "run_ibge_indicators", _run_ibge_indicators)
    monkeypatch.setattr(prefect_flows, "run_tse_catalog", _run_tse_catalog)
    monkeypatch.setattr(prefect_flows, "run_tse_electorate", _run_tse_electorate)
    monkeypatch.setattr(prefect_flows, "run_tse_results", _run_tse_results)
    monkeypatch.setattr(prefect_flows, "run_inep_education", _run_inep)
    monkeypatch.setattr(prefect_flows, "run_datasus_health", _run_datasus)
    monkeypatch.setattr(prefect_flows, "run_siconfi_finance", _run_siconfi)
    monkeypatch.setattr(prefect_flows, "run_mte_labor", _run_mte)

    def _run_sidra(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "sidra_indicators_fetch", "status": "success", "rows_written": 10}

    def _run_senatran(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "senatran_fleet_fetch", "status": "success", "rows_written": 11}

    def _run_sejusp(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "sejusp_public_safety_fetch", "status": "success", "rows_written": 12}

    def _run_siops(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "siops_health_finance_fetch", "status": "success", "rows_written": 13}

    def _run_snis(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "snis_sanitation_fetch", "status": "success", "rows_written": 14}

    def _run_inmet(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "inmet_climate_fetch", "status": "success", "rows_written": 15}

    def _run_inpe(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "inpe_queimadas_fetch", "status": "success", "rows_written": 16}

    def _run_ana(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "ana_hydrology_fetch", "status": "success", "rows_written": 17}

    def _run_anatel(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "anatel_connectivity_fetch", "status": "success", "rows_written": 18}

    def _run_aneel(**_kwargs: Any) -> dict[str, Any]:
        return {"job": "aneel_energy_fetch", "status": "success", "rows_written": 19}

    monkeypatch.setattr(prefect_flows, "run_sidra_indicators", _run_sidra)
    monkeypatch.setattr(prefect_flows, "run_senatran_fleet", _run_senatran)
    monkeypatch.setattr(prefect_flows, "run_sejusp_public_safety", _run_sejusp)
    monkeypatch.setattr(prefect_flows, "run_siops_health_finance", _run_siops)
    monkeypatch.setattr(prefect_flows, "run_snis_sanitation", _run_snis)
    monkeypatch.setattr(prefect_flows, "run_inmet_climate", _run_inmet)
    monkeypatch.setattr(prefect_flows, "run_inpe_queimadas", _run_inpe)
    monkeypatch.setattr(prefect_flows, "run_ana_hydrology", _run_ana)
    monkeypatch.setattr(prefect_flows, "run_anatel_connectivity", _run_anatel)
    monkeypatch.setattr(prefect_flows, "run_aneel_energy", _run_aneel)
    monkeypatch.setattr(prefect_flows, "run_dbt_build", _run_dbt)
    monkeypatch.setattr(prefect_flows, "run_quality_suite", _run_quality)

    result = prefect_flows.run_mvp_all.fn(reference_period="2024", dry_run=True)

    assert result["ibge_admin_fetch"]["rows_written"] == 1
    assert result["ibge_geometries_fetch"]["rows_written"] == 2
    assert result["ibge_indicators_fetch"]["rows_written"] == 3
    assert result["tse_catalog_discovery"]["rows_written"] == 4
    assert result["tse_electorate_fetch"]["rows_written"] == 5
    assert result["tse_results_fetch"]["rows_written"] == 6
    assert result["education_inep_fetch"]["rows_written"] == 7
    assert result["health_datasus_fetch"]["rows_written"] == 8
    assert result["finance_siconfi_fetch"]["rows_written"] == 9
    assert result["labor_mte_fetch"]["status"] == "blocked"
    assert result["sidra_indicators_fetch"]["rows_written"] == 10
    assert result["senatran_fleet_fetch"]["rows_written"] == 11
    assert result["sejusp_public_safety_fetch"]["rows_written"] == 12
    assert result["siops_health_finance_fetch"]["rows_written"] == 13
    assert result["snis_sanitation_fetch"]["rows_written"] == 14
    assert result["inmet_climate_fetch"]["rows_written"] == 15
    assert result["inpe_queimadas_fetch"]["rows_written"] == 16
    assert result["ana_hydrology_fetch"]["rows_written"] == 17
    assert result["anatel_connectivity_fetch"]["rows_written"] == 18
    assert result["aneel_energy_fetch"]["rows_written"] == 19
    assert result["dbt_build"]["models_built"] == 3
    assert result["quality_suite"]["job"] == "quality_suite"


def test_run_mvp_wave_4_propagates_common_kwargs_to_all_jobs(monkeypatch) -> None:
    calls: dict[str, dict[str, Any]] = {}

    def _stub(job_name: str):
        def _run(**kwargs: Any) -> dict[str, Any]:
            calls[job_name] = kwargs
            return {"job": job_name, "status": "success", "rows_written": 1}

        return _run

    monkeypatch.setattr(prefect_flows, "run_sidra_indicators", _stub("sidra_indicators_fetch"))
    monkeypatch.setattr(prefect_flows, "run_senatran_fleet", _stub("senatran_fleet_fetch"))
    monkeypatch.setattr(
        prefect_flows,
        "run_sejusp_public_safety",
        _stub("sejusp_public_safety_fetch"),
    )
    monkeypatch.setattr(
        prefect_flows,
        "run_siops_health_finance",
        _stub("siops_health_finance_fetch"),
    )
    monkeypatch.setattr(prefect_flows, "run_snis_sanitation", _stub("snis_sanitation_fetch"))
    monkeypatch.setattr(prefect_flows, "run_quality_suite", _stub("quality_suite"))

    result = prefect_flows.run_mvp_wave_4.fn(
        reference_period="2025",
        force=True,
        dry_run=False,
        max_retries=5,
        timeout_seconds=45,
    )

    assert set(result.keys()) == {
        "sidra_indicators_fetch",
        "senatran_fleet_fetch",
        "sejusp_public_safety_fetch",
        "siops_health_finance_fetch",
        "snis_sanitation_fetch",
        "quality_suite",
    }
    expected_kwargs = {
        "reference_period": "2025",
        "force": True,
        "dry_run": False,
        "max_retries": 5,
        "timeout_seconds": 45,
    }
    for job_name in result:
        assert calls[job_name] == expected_kwargs


def test_run_mvp_wave_5_propagates_common_kwargs_to_all_jobs(monkeypatch) -> None:
    calls: dict[str, dict[str, Any]] = {}

    def _stub(job_name: str):
        def _run(**kwargs: Any) -> dict[str, Any]:
            calls[job_name] = kwargs
            return {"job": job_name, "status": "success", "rows_written": 1}

        return _run

    monkeypatch.setattr(prefect_flows, "run_inmet_climate", _stub("inmet_climate_fetch"))
    monkeypatch.setattr(prefect_flows, "run_inpe_queimadas", _stub("inpe_queimadas_fetch"))
    monkeypatch.setattr(prefect_flows, "run_ana_hydrology", _stub("ana_hydrology_fetch"))
    monkeypatch.setattr(prefect_flows, "run_anatel_connectivity", _stub("anatel_connectivity_fetch"))
    monkeypatch.setattr(prefect_flows, "run_aneel_energy", _stub("aneel_energy_fetch"))
    monkeypatch.setattr(prefect_flows, "run_quality_suite", _stub("quality_suite"))

    result = prefect_flows.run_mvp_wave_5.fn(
        reference_period="2025",
        force=True,
        dry_run=False,
        max_retries=5,
        timeout_seconds=45,
    )

    assert set(result.keys()) == {
        "inmet_climate_fetch",
        "inpe_queimadas_fetch",
        "ana_hydrology_fetch",
        "anatel_connectivity_fetch",
        "aneel_energy_fetch",
        "quality_suite",
    }
    expected_kwargs = {
        "reference_period": "2025",
        "force": True,
        "dry_run": False,
        "max_retries": 5,
        "timeout_seconds": 45,
    }
    for job_name in result:
        assert calls[job_name] == expected_kwargs
