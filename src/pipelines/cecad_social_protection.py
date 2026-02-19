from __future__ import annotations

from pathlib import Path
from typing import Any

from app.settings import Settings
from pipelines.common.social_tabular_connector import (
    SocialConnectorDefinition,
    SocialMetricSpec,
    run_social_connector,
)

JOB_NAME = "cecad_social_protection_fetch"

_DEFINITION = SocialConnectorDefinition(
    job_name=JOB_NAME,
    source="CECAD",
    dataset_name="cecad_social_protection_catalog",
    fact_dataset_name="cecad_social_protection_municipal",
    wave="MVP-6",
    catalog_path=Path("configs/cecad_social_protection_catalog.yml"),
    manual_dir=Path("data/manual/cecad"),
    dataset_version="v1",
    notes="CECAD/CadUnico social protection indicators with Bronze snapshot and Silver social facts.",
    fact_table="silver.fact_social_protection",
    reference_year_columns=("ano", "referencia", "competencia"),
    prefer_manual_first=True,
    metric_specs=(
        SocialMetricSpec(
            field_name="households_total",
            indicator_code="CECAD_HOUSEHOLDS_TOTAL",
            indicator_name="CadUnico households total",
            unit="count",
            category="protecao_social",
            candidates=(
                "familias_cadunico_total",
                "familias_total",
                "qtd_familias",
            ),
            aggregator="sum",
        ),
        SocialMetricSpec(
            field_name="people_total",
            indicator_code="CECAD_PEOPLE_TOTAL",
            indicator_name="CadUnico people total",
            unit="count",
            category="protecao_social",
            candidates=(
                "pessoas_cadunico_total",
                "pessoas_total",
                "qtd_pessoas",
            ),
            aggregator="sum",
        ),
        SocialMetricSpec(
            field_name="avg_income_per_capita",
            indicator_code="CECAD_AVG_INCOME_PER_CAPITA",
            indicator_name="CadUnico average income per capita",
            unit="BRL",
            category="protecao_social",
            candidates=(
                "renda_media_per_capita",
                "renda_per_capita_media",
                "vlr_media_renda_per_capita",
            ),
            aggregator="avg",
        ),
        SocialMetricSpec(
            field_name="poverty_rate",
            indicator_code="CECAD_POVERTY_RATE",
            indicator_name="CadUnico poverty rate",
            unit="percent",
            category="protecao_social",
            candidates=(
                "percentual_pobreza",
                "taxa_pobreza",
                "perc_pobreza",
            ),
            aggregator="avg",
        ),
        SocialMetricSpec(
            field_name="extreme_poverty_rate",
            indicator_code="CECAD_EXTREME_POVERTY_RATE",
            indicator_name="CadUnico extreme poverty rate",
            unit="percent",
            category="protecao_social",
            candidates=(
                "percentual_extrema_pobreza",
                "taxa_extrema_pobreza",
                "perc_extrema_pobreza",
            ),
            aggregator="avg",
        ),
    ),
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
    return run_social_connector(
        _DEFINITION,
        reference_period=reference_period,
        force=force,
        dry_run=dry_run,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
        settings=settings,
    )
