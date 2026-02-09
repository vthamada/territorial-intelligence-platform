from __future__ import annotations

from typing import Any

from app.settings import get_settings
from pipelines.common.source_probe import run_source_probe_job

JOB_NAME = "health_datasus_fetch"


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
        source="DATASUS",
        dataset_name="datasus_health_probe",
        indicator_code="DATASUS_SOURCE_PROBE",
        indicator_name="DATASUS source probe count",
        probe_urls=[
            "https://opendatasus.saude.gov.br/",
            "https://www.gov.br/saude/pt-br/acesso-a-informacao/dados-abertos",
        ],
        reference_period=reference_period,
        wave="MVP-3",
        settings=settings,
        dry_run=dry_run,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    )
