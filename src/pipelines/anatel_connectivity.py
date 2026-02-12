from __future__ import annotations

from pathlib import Path
from typing import Any

from app.settings import Settings
from pipelines.common.tabular_indicator_connector import (
    IndicatorSpec,
    TabularConnectorDefinition,
    run_tabular_connector,
)

JOB_NAME = "anatel_connectivity_fetch"
SOURCE = "ANATEL"
DATASET_NAME = "anatel_connectivity_catalog"
FACT_DATASET_NAME = "anatel_connectivity_municipal"
WAVE = "MVP-5"
ANATEL_CATALOG_PATH = Path("configs/anatel_connectivity_catalog.yml")
MANUAL_ANATEL_DIR = Path("data/manual/anatel")

DEFINITION = TabularConnectorDefinition(
    job_name=JOB_NAME,
    source=SOURCE,
    dataset_name=DATASET_NAME,
    fact_dataset_name=FACT_DATASET_NAME,
    wave=WAVE,
    catalog_path=ANATEL_CATALOG_PATH,
    manual_dir=MANUAL_ANATEL_DIR,
    indicator_specs=(
        IndicatorSpec(
            code="ANATEL_ACESSOS_BANDA_LARGA_FIXA",
            name="ANATEL acessos de banda larga fixa",
            unit="count",
            category="conectividade",
            candidates=("acessos_banda_larga_fixa", "acessos_scm", "acessos_fixos", "acessos"),
            aggregator="sum",
            row_filters={"servico": ("banda larga fixa",)},
        ),
        IndicatorSpec(
            code="ANATEL_ACESSOS_BANDA_LARGA_MOVEL",
            name="ANATEL acessos de banda larga movel",
            unit="count",
            category="conectividade",
            candidates=("acessos_banda_larga_movel", "acessos_smp_dados", "acessos_moveis", "acessos"),
            aggregator="sum",
            row_filters={"servico": ("telefonia movel", "banda larga movel")},
        ),
        IndicatorSpec(
            code="ANATEL_DENSIDADE_BANDA_LARGA_FIXA_100HAB",
            name="ANATEL densidade de banda larga fixa por 100 habitantes",
            unit="ratio",
            category="conectividade",
            candidates=("densidade_banda_larga_fixa_100hab", "densidade_100hab", "densidade"),
            aggregator="avg",
            row_filters={"servico": ("banda larga fixa",)},
        ),
    ),
    dataset_version="anatel-connectivity-v1",
    notes="ANATEL connectivity extraction and indicator upsert.",
    reference_year_columns=("ano",),
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
