from __future__ import annotations

import os
from pathlib import Path
from tempfile import gettempdir
from typing import Any

# Ensure Prefect metadata storage is writable in local/dev environments.
if "PREFECT_HOME" not in os.environ:
    default_prefect_home = Path(gettempdir()) / "prefect-home"
    default_prefect_home.mkdir(parents=True, exist_ok=True)
    os.environ["PREFECT_HOME"] = str(default_prefect_home)

# Ensure ephemeral Prefect API DB is also placed on a writable local-temp path.
if "PREFECT_API_DATABASE_CONNECTION_URL" not in os.environ:
    default_prefect_db = Path(gettempdir()) / "prefect-home" / "orion.db"
    default_prefect_db.parent.mkdir(parents=True, exist_ok=True)
    os.environ["PREFECT_API_DATABASE_CONNECTION_URL"] = (
        f"sqlite+aiosqlite:///{default_prefect_db.as_posix()}"
    )

if "PREFECT_MEMO_STORE_PATH" not in os.environ:
    default_memo_store = Path(os.environ["PREFECT_HOME"]) / "memo_store.toml"
    default_memo_store.parent.mkdir(parents=True, exist_ok=True)
    os.environ["PREFECT_MEMO_STORE_PATH"] = str(default_memo_store)

from prefect import flow

from app.logging import configure_logging
from app.settings import get_settings
from pipelines.datasus_health import run as run_datasus_health
from pipelines.dbt_build import run as run_dbt_build
from pipelines.ibge_admin import run as run_ibge_admin
from pipelines.ibge_geometries import run as run_ibge_geometries
from pipelines.ibge_indicators import run as run_ibge_indicators
from pipelines.inmet_climate import run as run_inmet_climate
from pipelines.inep_education import run as run_inep_education
from pipelines.inpe_queimadas import run as run_inpe_queimadas
from pipelines.mte_labor import run as run_mte_labor
from pipelines.ana_hydrology import run as run_ana_hydrology
from pipelines.anatel_connectivity import run as run_anatel_connectivity
from pipelines.aneel_energy import run as run_aneel_energy
from pipelines.cecad_social_protection import run as run_cecad_social_protection
from pipelines.censo_suas import run as run_censo_suas
from pipelines.urban_roads import run as run_urban_roads
from pipelines.urban_pois import run as run_urban_pois
from pipelines.quality_suite import run as run_quality_suite
from pipelines.sejusp_public_safety import run as run_sejusp_public_safety
from pipelines.senatran_fleet import run as run_senatran_fleet
from pipelines.siconfi_finance import run as run_siconfi_finance
from pipelines.sidra_indicators import run as run_sidra_indicators
from pipelines.siops_health_finance import run as run_siops_health_finance
from pipelines.snis_sanitation import run as run_snis_sanitation
from pipelines.tse_catalog import run as run_tse_catalog
from pipelines.tse_electorate import run as run_tse_electorate
from pipelines.tse_results import run as run_tse_results

settings = get_settings()
configure_logging(settings.log_level)


@flow(name="ibge_admin_fetch")
def ibge_admin_fetch(
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    return run_ibge_admin(
        reference_period=reference_period,
        force=force,
        dry_run=dry_run,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    )


@flow(name="territorial_mvp_flow")
def run_mvp_all(
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    common_kwargs = {
        "reference_period": reference_period,
        "force": force,
        "dry_run": dry_run,
        "max_retries": max_retries,
        "timeout_seconds": timeout_seconds,
    }
    results = {
        "ibge_admin_fetch": run_ibge_admin(**common_kwargs),
        "ibge_geometries_fetch": run_ibge_geometries(**common_kwargs),
        "ibge_indicators_fetch": run_ibge_indicators(**common_kwargs),
        "tse_catalog_discovery": run_tse_catalog(**common_kwargs),
        "tse_electorate_fetch": run_tse_electorate(**common_kwargs),
        "tse_results_fetch": run_tse_results(**common_kwargs),
        "education_inep_fetch": run_inep_education(**common_kwargs),
        "health_datasus_fetch": run_datasus_health(**common_kwargs),
        "finance_siconfi_fetch": run_siconfi_finance(**common_kwargs),
        "labor_mte_fetch": run_mte_labor(**common_kwargs),
        "sidra_indicators_fetch": run_sidra_indicators(**common_kwargs),
        "senatran_fleet_fetch": run_senatran_fleet(**common_kwargs),
        "sejusp_public_safety_fetch": run_sejusp_public_safety(**common_kwargs),
        "siops_health_finance_fetch": run_siops_health_finance(**common_kwargs),
        "snis_sanitation_fetch": run_snis_sanitation(**common_kwargs),
        "inmet_climate_fetch": run_inmet_climate(**common_kwargs),
        "inpe_queimadas_fetch": run_inpe_queimadas(**common_kwargs),
        "ana_hydrology_fetch": run_ana_hydrology(**common_kwargs),
        "anatel_connectivity_fetch": run_anatel_connectivity(**common_kwargs),
        "aneel_energy_fetch": run_aneel_energy(**common_kwargs),
        "cecad_social_protection_fetch": run_cecad_social_protection(**common_kwargs),
        "censo_suas_fetch": run_censo_suas(**common_kwargs),
        "urban_roads_fetch": run_urban_roads(**common_kwargs),
        "urban_pois_fetch": run_urban_pois(**common_kwargs),
        "dbt_build": run_dbt_build(**common_kwargs),
        "quality_suite": run_quality_suite(**common_kwargs),
    }
    return results


@flow(name="territorial_mvp_wave_1")
def run_mvp_wave_1(
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    common_kwargs = {
        "reference_period": reference_period,
        "force": force,
        "dry_run": dry_run,
        "max_retries": max_retries,
        "timeout_seconds": timeout_seconds,
    }
    return {
        "ibge_admin_fetch": run_ibge_admin(**common_kwargs),
        "ibge_geometries_fetch": run_ibge_geometries(**common_kwargs),
        "ibge_indicators_fetch": run_ibge_indicators(**common_kwargs),
        "dbt_build": run_dbt_build(**common_kwargs),
        "quality_suite": run_quality_suite(**common_kwargs),
    }


@flow(name="territorial_mvp_wave_2")
def run_mvp_wave_2(
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    common_kwargs = {
        "reference_period": reference_period,
        "force": force,
        "dry_run": dry_run,
        "max_retries": max_retries,
        "timeout_seconds": timeout_seconds,
    }
    return {
        "tse_catalog_discovery": run_tse_catalog(**common_kwargs),
        "tse_electorate_fetch": run_tse_electorate(**common_kwargs),
        "tse_results_fetch": run_tse_results(**common_kwargs),
        "quality_suite": run_quality_suite(**common_kwargs),
    }


@flow(name="territorial_mvp_wave_3")
def run_mvp_wave_3(
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    common_kwargs = {
        "reference_period": reference_period,
        "force": force,
        "dry_run": dry_run,
        "max_retries": max_retries,
        "timeout_seconds": timeout_seconds,
    }
    return {
        "education_inep_fetch": run_inep_education(**common_kwargs),
        "health_datasus_fetch": run_datasus_health(**common_kwargs),
        "finance_siconfi_fetch": run_siconfi_finance(**common_kwargs),
        "labor_mte_fetch": run_mte_labor(**common_kwargs),
        "quality_suite": run_quality_suite(**common_kwargs),
    }


@flow(name="territorial_mvp_wave_4")
def run_mvp_wave_4(
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    common_kwargs = {
        "reference_period": reference_period,
        "force": force,
        "dry_run": dry_run,
        "max_retries": max_retries,
        "timeout_seconds": timeout_seconds,
    }
    return {
        "sidra_indicators_fetch": run_sidra_indicators(**common_kwargs),
        "senatran_fleet_fetch": run_senatran_fleet(**common_kwargs),
        "sejusp_public_safety_fetch": run_sejusp_public_safety(**common_kwargs),
        "siops_health_finance_fetch": run_siops_health_finance(**common_kwargs),
        "snis_sanitation_fetch": run_snis_sanitation(**common_kwargs),
        "quality_suite": run_quality_suite(**common_kwargs),
    }


@flow(name="territorial_mvp_wave_5")
def run_mvp_wave_5(
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    common_kwargs = {
        "reference_period": reference_period,
        "force": force,
        "dry_run": dry_run,
        "max_retries": max_retries,
        "timeout_seconds": timeout_seconds,
    }
    return {
        "inmet_climate_fetch": run_inmet_climate(**common_kwargs),
        "inpe_queimadas_fetch": run_inpe_queimadas(**common_kwargs),
        "ana_hydrology_fetch": run_ana_hydrology(**common_kwargs),
        "anatel_connectivity_fetch": run_anatel_connectivity(**common_kwargs),
        "aneel_energy_fetch": run_aneel_energy(**common_kwargs),
        "quality_suite": run_quality_suite(**common_kwargs),
    }


@flow(name="territorial_mvp_wave_6")
def run_mvp_wave_6(
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    common_kwargs = {
        "reference_period": reference_period,
        "force": force,
        "dry_run": dry_run,
        "max_retries": max_retries,
        "timeout_seconds": timeout_seconds,
    }
    return {
        "cecad_social_protection_fetch": run_cecad_social_protection(**common_kwargs),
        "censo_suas_fetch": run_censo_suas(**common_kwargs),
        "quality_suite": run_quality_suite(**common_kwargs),
    }


@flow(name="territorial_mvp_wave_7")
def run_mvp_wave_7(
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    common_kwargs = {
        "reference_period": reference_period,
        "force": force,
        "dry_run": dry_run,
        "max_retries": max_retries,
        "timeout_seconds": timeout_seconds,
    }
    return {
        "urban_roads_fetch": run_urban_roads(**common_kwargs),
        "urban_pois_fetch": run_urban_pois(**common_kwargs),
        "quality_suite": run_quality_suite(**common_kwargs),
    }


def run_mvp(*args, **kwargs) -> dict[str, Any]:
    return run_mvp_all(*args, **kwargs)
