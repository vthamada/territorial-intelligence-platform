from __future__ import annotations

from typing import Any

from app.settings import get_settings
from pipelines.common.source_probe import run_source_probe_job

JOB_NAME = "finance_siconfi_fetch"


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
        source="SICONFI",
        dataset_name="siconfi_finance_probe",
        indicator_code="SICONFI_SOURCE_PROBE",
        indicator_name="SICONFI source probe count",
        probe_urls=[
            "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo?limit=1",
            "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rgf?limit=1",
            "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca?limit=1",
        ],
        reference_period=reference_period,
        wave="MVP-3",
        settings=settings,
        dry_run=dry_run,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    )
