from __future__ import annotations

from typing import Any

from app.settings import get_settings
from pipelines.common.source_probe import run_source_probe_job

JOB_NAME = "education_inep_fetch"


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
        source="INEP",
        dataset_name="inep_education_probe",
        indicator_code="INEP_SOURCE_PROBE",
        indicator_name="INEP source probe count",
        probe_urls=[
            "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos",
            "https://dadosabertos.inep.gov.br/api/3/action/package_search?q=censo%20escolar&rows=1",
        ],
        reference_period=reference_period,
        wave="MVP-3",
        settings=settings,
        dry_run=dry_run,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    )
