from __future__ import annotations

from pathlib import Path
from typing import Any

from app.settings import Settings
from pipelines.common.tabular_indicator_connector import (
    IndicatorSpec,
    TabularConnectorDefinition,
    run_tabular_connector,
)

JOB_NAME = "inpe_queimadas_fetch"
SOURCE = "INPE_QUEIMADAS"
DATASET_NAME = "inpe_queimadas_catalog"
FACT_DATASET_NAME = "inpe_queimadas_municipal"
WAVE = "MVP-5"
INPE_CATALOG_PATH = Path("configs/inpe_queimadas_catalog.yml")
MANUAL_INPE_DIR = Path("data/manual/inpe_queimadas")

DEFINITION = TabularConnectorDefinition(
    job_name=JOB_NAME,
    source=SOURCE,
    dataset_name=DATASET_NAME,
    fact_dataset_name=FACT_DATASET_NAME,
    wave=WAVE,
    catalog_path=INPE_CATALOG_PATH,
    manual_dir=MANUAL_INPE_DIR,
    indicator_specs=(
        IndicatorSpec(
            code="INPE_FOCOS_QUEIMADAS_TOTAL",
            name="INPE focos de queimadas",
            unit="count",
            category="meio_ambiente",
            candidates=("focos_total", "focos", "numero_focos", "qtd_focos"),
            aggregator="sum",
        ),
        IndicatorSpec(
            code="INPE_AREA_QUEIMADA_HA",
            name="INPE area queimada",
            unit="ha",
            category="meio_ambiente",
            candidates=("area_queimada_ha", "area_queimada", "area_ha"),
            aggregator="sum",
        ),
        IndicatorSpec(
            code="INPE_RISCO_FOGO_INDICE",
            name="INPE indice de risco de fogo",
            unit="index",
            category="meio_ambiente",
            candidates=("risco_fogo_indice", "risco_fogo", "indice_risco"),
            aggregator="max",
        ),
    ),
    dataset_version="inpe-queimadas-v1",
    notes="INPE queimadas extraction and indicator upsert.",
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
