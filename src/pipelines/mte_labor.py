from __future__ import annotations

from typing import Any

from app.settings import get_settings
from pipelines.common.source_probe import run_source_probe_job

JOB_NAME = "labor_mte_fetch"


def run(
    *,
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    del force
    settings = get_settings()
    return run_source_probe_job(
        job_name=JOB_NAME,
        source="MTE",
        dataset_name="mte_labor_probe",
        indicator_code="MTE_SOURCE_PROBE",
        indicator_name="MTE source probe count",
        probe_urls=[
            "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/novo-caged",
            "https://dados.gov.br/dados/conjuntos-dados/novo-caged",
        ],
        reference_period=reference_period,
        wave="MVP-3",
        settings=settings,
        dry_run=dry_run,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    )
