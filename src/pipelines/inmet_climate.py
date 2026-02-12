from __future__ import annotations

from pathlib import Path
from typing import Any

from app.settings import Settings
from pipelines.common.tabular_indicator_connector import (
    IndicatorSpec,
    TabularConnectorDefinition,
    run_tabular_connector,
)

JOB_NAME = "inmet_climate_fetch"
SOURCE = "INMET"
DATASET_NAME = "inmet_climate_catalog"
FACT_DATASET_NAME = "inmet_climate_municipal"
WAVE = "MVP-5"
INMET_CATALOG_PATH = Path("configs/inmet_climate_catalog.yml")
MANUAL_INMET_DIR = Path("data/manual/inmet")

DEFINITION = TabularConnectorDefinition(
    job_name=JOB_NAME,
    source=SOURCE,
    dataset_name=DATASET_NAME,
    fact_dataset_name=FACT_DATASET_NAME,
    wave=WAVE,
    catalog_path=INMET_CATALOG_PATH,
    manual_dir=MANUAL_INMET_DIR,
    indicator_specs=(
        IndicatorSpec(
            code="INMET_PRECIPITACAO_TOTAL_MM",
            name="INMET precipitacao total",
            unit="mm",
            category="clima",
            candidates=(
                "precipitacao_total_mm",
                "precipitacao_total_horario_mm",
                "precipitacao_mm",
                "chuva_mm",
                "precipitacao",
            ),
            aggregator="sum",
        ),
        IndicatorSpec(
            code="INMET_TEMPERATURA_MEDIA_C",
            name="INMET temperatura media",
            unit="C",
            category="clima",
            candidates=("temperatura_media_c", "temperatura_media", "temp_media", "tmed"),
            aggregator="avg",
        ),
        IndicatorSpec(
            code="INMET_UMIDADE_RELATIVA_MEDIA_PERCENT",
            name="INMET umidade relativa media",
            unit="percent",
            category="clima",
            candidates=(
                "umidade_relativa_media_percent",
                "umidade_relativa_do_ar_horaria",
                "umidade_media",
                "ur_media",
            ),
            aggregator="avg",
        ),
    ),
    dataset_version="inmet-climate-v1",
    notes="INMET climate extraction and indicator upsert.",
)


def run(
    *,
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
    settings: Settings | None = None,
) -> dict[str, Any]:
    return run_tabular_connector(
        DEFINITION,
        reference_period=reference_period,
        force=force,
        dry_run=dry_run,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
        settings=settings,
    )
