from __future__ import annotations

from pathlib import Path
from typing import Any

from app.settings import Settings
from pipelines.common.tabular_indicator_connector import (
    IndicatorSpec,
    TabularConnectorDefinition,
    run_tabular_connector,
)

JOB_NAME = "ana_hydrology_fetch"
SOURCE = "ANA"
DATASET_NAME = "ana_hydrology_catalog"
FACT_DATASET_NAME = "ana_hydrology_municipal"
WAVE = "MVP-5"
ANA_CATALOG_PATH = Path("configs/ana_hydrology_catalog.yml")
MANUAL_ANA_DIR = Path("data/manual/ana")

DEFINITION = TabularConnectorDefinition(
    job_name=JOB_NAME,
    source=SOURCE,
    dataset_name=DATASET_NAME,
    fact_dataset_name=FACT_DATASET_NAME,
    wave=WAVE,
    catalog_path=ANA_CATALOG_PATH,
    manual_dir=MANUAL_ANA_DIR,
    indicator_specs=(
        IndicatorSpec(
            code="ANA_PRECIPITACAO_TOTAL_MM",
            name="ANA precipitacao total",
            unit="mm",
            category="recursos_hidricos",
            candidates=(
                "precipitacao_total_mm",
                "precipitacao_mm",
                "chuva_mm",
                "precipitacao",
                "chuva",
                "prec_mm",
            ),
            aggregator="sum",
        ),
        IndicatorSpec(
            code="ANA_VAZAO_MEDIA_M3S",
            name="ANA vazao media",
            unit="m3/s",
            category="recursos_hidricos",
            candidates=(
                "vazao_media_m3s",
                "vztotm3s",
                "vazao_media",
                "vazao",
                "vazao_retirada_m3s",
                "vazao_retirada",
                "q_ret_m3s",
                "qret_m3s",
                "vazret_m3s",
            ),
            aggregator="avg",
        ),
        IndicatorSpec(
            code="ANA_NIVEL_MEDIO_M",
            name="ANA nivel medio",
            unit="m",
            category="recursos_hidricos",
            candidates=("nivel_medio_m", "nivel_medio", "nivel", "nivel_medio"),
            aggregator="avg",
        ),
    ),
    dataset_version="ana-hydrology-v1",
    notes="ANA hydrology extraction and indicator upsert.",
    municipality_code_columns=(
        "municipio_ibge",
        "codigo_municipio",
        "cod_municipio",
        "cdmun",
        "codmunres",
        "cod_ibge",
        "codigo_ibge",
        "codigo_ibge_7",
        "id_municipio",
        "ibge",
        "cd_mun",
        "codmunicipio",
        "cod_municipio_ibge",
    ),
    municipality_name_columns=(
        "municipio",
        "nome_municipio",
        "nmmun",
        "nm_municipio",
        "nom_municipio",
        "cidade",
        "localidade",
    ),
    reference_year_columns=("ano", "ano_ref", "anoindice", "datreferenciainformada"),
)


def run(
    *,
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 2,
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
