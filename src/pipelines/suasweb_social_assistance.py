from __future__ import annotations

from pathlib import Path
from typing import Any

from app.settings import Settings
from pipelines.common.tabular_indicator_connector import (
    IndicatorSpec,
    TabularConnectorDefinition,
    run_tabular_connector,
)

JOB_NAME = "suasweb_social_assistance_fetch"
SOURCE = "SUASWEB"
DATASET_NAME = "suasweb_social_assistance_catalog"
FACT_DATASET_NAME = "suasweb_social_assistance_municipal"
WAVE = "MVP-6"
SUASWEB_CATALOG_PATH = Path("configs/suasweb_social_assistance_catalog.yml")
MANUAL_SUASWEB_DIR = Path("data/manual/suasweb")

DEFINITION = TabularConnectorDefinition(
    job_name=JOB_NAME,
    source=SOURCE,
    dataset_name=DATASET_NAME,
    fact_dataset_name=FACT_DATASET_NAME,
    wave=WAVE,
    catalog_path=SUASWEB_CATALOG_PATH,
    manual_dir=MANUAL_SUASWEB_DIR,
    indicator_specs=(
        IndicatorSpec(
            code="SUAS_REPASSE_TOTAL_FUNDO_MUNICIPAL",
            name="SUAS repasse total fundo municipal",
            unit="BRL",
            category="assistencia_social",
            candidates=("suas_repasse_mun_vl_total_fundo_f",),
            aggregator="sum",
        ),
        IndicatorSpec(
            code="SUAS_REPASSE_PSB",
            name="SUAS repasse protecao social basica",
            unit="BRL",
            category="assistencia_social",
            candidates=("suas_repasse_mun_vl_psb_f",),
            aggregator="sum",
        ),
        IndicatorSpec(
            code="SUAS_REPASSE_PSE_TOTAL",
            name="SUAS repasse protecao social especial total",
            unit="BRL",
            category="assistencia_social",
            candidates=("suas_repasse_mun_vl_pse_f",),
            aggregator="sum",
        ),
        IndicatorSpec(
            code="SUAS_REPASSE_GESTAO_SUAS",
            name="SUAS repasse gestao do SUAS",
            unit="BRL",
            category="assistencia_social",
            candidates=("suas_repasse_mun_vl_gestao_suas_f",),
            aggregator="sum",
        ),
        IndicatorSpec(
            code="SUAS_REPASSE_GESTAO_CADUNICO",
            name="SUAS repasse gestao PBF/CadUnico",
            unit="BRL",
            category="assistencia_social",
            candidates=("suas_repasse_mun_vl_gestao_pbf_cadun_f",),
            aggregator="sum",
        ),
    ),
    dataset_version="suasweb-social-assistance-v1",
    notes="SUASWEB municipal transfers for socio-assistance analytics with open access source.",
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
