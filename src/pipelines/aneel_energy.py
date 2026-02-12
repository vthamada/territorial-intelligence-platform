from __future__ import annotations

from pathlib import Path
from typing import Any

from app.settings import Settings
from pipelines.common.tabular_indicator_connector import (
    IndicatorSpec,
    TabularConnectorDefinition,
    run_tabular_connector,
)

JOB_NAME = "aneel_energy_fetch"
SOURCE = "ANEEL"
DATASET_NAME = "aneel_energy_catalog"
FACT_DATASET_NAME = "aneel_energy_municipal"
WAVE = "MVP-5"
ANEEL_CATALOG_PATH = Path("configs/aneel_energy_catalog.yml")
MANUAL_ANEEL_DIR = Path("data/manual/aneel")

DEFINITION = TabularConnectorDefinition(
    job_name=JOB_NAME,
    source=SOURCE,
    dataset_name=DATASET_NAME,
    fact_dataset_name=FACT_DATASET_NAME,
    wave=WAVE,
    catalog_path=ANEEL_CATALOG_PATH,
    manual_dir=MANUAL_ANEEL_DIR,
    indicator_specs=(
        IndicatorSpec(
            code="ANEEL_CONSUMO_TOTAL_MWH",
            name="ANEEL consumo total de energia",
            unit="MWh",
            category="energia",
            candidates=("consumo_total_mwh", "consumo_mwh", "energia_consumida_mwh", "consumo"),
            aggregator="sum",
        ),
        IndicatorSpec(
            code="ANEEL_UNIDADES_CONSUMIDORAS_TOTAL",
            name="ANEEL unidades consumidoras",
            unit="count",
            category="energia",
            candidates=("unidades_consumidoras_total", "uc_total", "unidades_consumidoras", "uc"),
            aggregator="sum",
        ),
        IndicatorSpec(
            code="ANEEL_DIC_MEDIO_HORAS",
            name="ANEEL DIC medio",
            unit="h",
            category="energia",
            candidates=("dic_medio_horas", "dic_horas", "dic"),
            aggregator="avg",
        ),
    ),
    dataset_version="aneel-energy-v1",
    notes="ANEEL energy extraction and indicator upsert.",
    municipality_code_columns=(
        "municipio_ibge",
        "codigo_municipio",
        "cod_municipio",
        "codmunres",
        "cod_ibge",
        "codigo_ibge",
        "codigo_ibge_7",
        "id_municipio",
        "ibge",
        "codmunicipioibge",
    ),
    reference_year_columns=("datreferenciainformada",),
    prefer_manual_first=True,
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
