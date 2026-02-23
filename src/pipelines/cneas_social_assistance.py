from __future__ import annotations

from pathlib import Path
from typing import Any

from app.settings import Settings
from pipelines.common.tabular_indicator_connector import (
    IndicatorSpec,
    TabularConnectorDefinition,
    run_tabular_connector,
)

JOB_NAME = "cneas_social_assistance_fetch"
SOURCE = "CNEAS"
DATASET_NAME = "cneas_social_assistance_catalog"
FACT_DATASET_NAME = "cneas_social_assistance_municipal"
WAVE = "MVP-6"
CNEAS_CATALOG_PATH = Path("configs/cneas_social_assistance_catalog.yml")
MANUAL_CNEAS_DIR = Path("data/manual/cneas")

DEFINITION = TabularConnectorDefinition(
    job_name=JOB_NAME,
    source=SOURCE,
    dataset_name=DATASET_NAME,
    fact_dataset_name=FACT_DATASET_NAME,
    wave=WAVE,
    catalog_path=CNEAS_CATALOG_PATH,
    manual_dir=MANUAL_CNEAS_DIR,
    indicator_specs=(
        IndicatorSpec(
            code="CNEAS_ENTIDADES_TOTAL",
            name="CNEAS total de entidades cadastradas",
            unit="count",
            category="assistencia_social",
            candidates=("cneas_cod_entidade_s",),
            aggregator="count",
        ),
        IndicatorSpec(
            code="CNEAS_OFERTAS_TOTAL",
            name="CNEAS total de ofertas socioassistenciais",
            unit="count",
            category="assistencia_social",
            candidates=("cneas_oferta_cod_servico_s",),
            aggregator="count",
        ),
        IndicatorSpec(
            code="CNEAS_OFERTAS_PROTECAO_BASICA",
            name="CNEAS ofertas de protecao basica",
            unit="count",
            category="assistencia_social",
            candidates=("cneas_oferta_cod_servico_s",),
            aggregator="count",
            row_filters={"cneas_oferta_desc_nivel_protecao_s": ("basica",)},
        ),
        IndicatorSpec(
            code="CNEAS_OFERTAS_PROTECAO_ESPECIAL",
            name="CNEAS ofertas de protecao especial",
            unit="count",
            category="assistencia_social",
            candidates=("cneas_oferta_cod_servico_s",),
            aggregator="count",
            row_filters={"cneas_oferta_desc_nivel_protecao_s": ("especial",)},
        ),
    ),
    dataset_version="cneas-social-assistance-v1",
    notes="CNEAS municipal entities and offers from open MISocial resources.",
    reference_year_columns=("anomes_s",),
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
