from __future__ import annotations

from pathlib import Path
from typing import Any

from app.settings import Settings
from pipelines.common.social_tabular_connector import (
    SocialConnectorDefinition,
    SocialMetricSpec,
    run_social_connector,
)

JOB_NAME = "censo_suas_fetch"

_DEFINITION = SocialConnectorDefinition(
    job_name=JOB_NAME,
    source="CENSO_SUAS",
    dataset_name="censo_suas_catalog",
    fact_dataset_name="censo_suas_assistance_network_municipal",
    wave="MVP-6",
    catalog_path=Path("configs/censo_suas_catalog.yml"),
    manual_dir=Path("data/manual/censo_suas"),
    dataset_version="v1",
    notes="Censo SUAS assistance network indicators with Bronze snapshot and Silver social facts.",
    fact_table="silver.fact_social_assistance_network",
    reference_year_columns=("ano", "referencia", "competencia"),
    prefer_manual_first=True,
    metric_specs=(
        SocialMetricSpec(
            field_name="cras_units",
            indicator_code="SUAS_CRAS_UNITS",
            indicator_name="CRAS units",
            unit="count",
            category="assistencia_social",
            candidates=("cras_total", "qtd_cras", "numero_cras"),
            aggregator="sum",
        ),
        SocialMetricSpec(
            field_name="creas_units",
            indicator_code="SUAS_CREAS_UNITS",
            indicator_name="CREAS units",
            unit="count",
            category="assistencia_social",
            candidates=("creas_total", "qtd_creas", "numero_creas"),
            aggregator="sum",
        ),
        SocialMetricSpec(
            field_name="social_units_total",
            indicator_code="SUAS_SOCIAL_UNITS_TOTAL",
            indicator_name="Social assistance units total",
            unit="count",
            category="assistencia_social",
            candidates=(
                "unidades_socioassistenciais_total",
                "unidades_total",
                "qtd_unidades",
            ),
            aggregator="sum",
        ),
        SocialMetricSpec(
            field_name="workers_total",
            indicator_code="SUAS_WORKERS_TOTAL",
            indicator_name="SUAS workers total",
            unit="count",
            category="assistencia_social",
            candidates=("trabalhadores_total", "qtd_trabalhadores", "equipe_total"),
            aggregator="sum",
        ),
        SocialMetricSpec(
            field_name="service_capacity_total",
            indicator_code="SUAS_SERVICE_CAPACITY_TOTAL",
            indicator_name="SUAS service capacity total",
            unit="count",
            category="assistencia_social",
            candidates=("capacidade_atendimento_total", "capacidade_total", "vagas_total"),
            aggregator="sum",
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
