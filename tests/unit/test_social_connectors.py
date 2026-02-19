from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from app.settings import Settings
from pipelines import cecad_social_protection, censo_suas
from pipelines.common import social_tabular_connector


def _build_settings() -> Settings:
    return Settings(
        municipality_ibge_code="3121605",
        database_url="postgresql+psycopg://postgres:postgres@localhost:5432/test_db",
    )


class _FakeHttpClient:
    def close(self) -> None:
        return None


@pytest.mark.parametrize(
    ("runner", "dataframe", "expected_metric"),
    [
        (
            cecad_social_protection.run,
            pd.DataFrame(
                [
                    {
                        "codigo_municipio": "3121605",
                        "familias_total": "1200",
                        "pessoas_total": "3500",
                        "renda_media_per_capita": "210.5",
                        "taxa_pobreza": "28.1",
                        "taxa_extrema_pobreza": "9.3",
                    }
                ]
            ),
            ("households_total", "1200"),
        ),
        (
            censo_suas.run,
            pd.DataFrame(
                [
                    {
                        "codigo_municipio": "3121605",
                        "qtd_cras": "4",
                        "qtd_creas": "1",
                        "qtd_unidades": "8",
                        "qtd_trabalhadores": "95",
                        "capacidade_total": "4100",
                    }
                ]
            ),
            ("cras_units", "4"),
        ),
    ],
)
def test_social_connectors_dry_run_uses_resolved_dataset(
    monkeypatch: pytest.MonkeyPatch,
    runner,
    dataframe: pd.DataFrame,
    expected_metric: tuple[str, str],
) -> None:
    monkeypatch.setattr(
        social_tabular_connector.tabular,
        "_resolve_municipality_context",
        lambda _settings: ("00000000-0000-0000-0000-000000000000", "Diamantina", "3121605"),
    )
    monkeypatch.setattr(
        social_tabular_connector.tabular,
        "_resolve_dataset",
        lambda **kwargs: (  # noqa: ARG005
            dataframe,
            b"raw",
            ".csv",
            "manual",
            "file:///tmp/social.csv",
            "social.csv",
            [],
        ),
    )
    monkeypatch.setattr(
        social_tabular_connector.HttpClient,
        "from_settings",
        lambda *args, **kwargs: _FakeHttpClient(),
    )

    result = runner(reference_period="2025", dry_run=True, settings=_build_settings())

    assert result["status"] == "success"
    assert result["rows_extracted"] == 1
    assert result["preview"]["source_type"] == "manual"
    metric_name, metric_value = expected_metric
    assert result["preview"]["metrics"][metric_name] == metric_value


def test_social_connector_aggregation_supports_avg_and_sum() -> None:
    municipality_rows = [
        {"familias_total": "100", "taxa_pobreza": "20"},
        {"familias_total": "140", "taxa_pobreza": "30"},
    ]
    definition = cecad_social_protection._DEFINITION  # noqa: SLF001
    metric_values, indicator_rows = social_tabular_connector._build_metrics_output(  # noqa: SLF001
        definition,
        territory_id="00000000-0000-0000-0000-000000000000",
        reference_period="2025",
        municipality_rows=municipality_rows,
    )

    assert metric_values["households_total"] == Decimal("240")
    assert metric_values["poverty_rate"] == Decimal("25")
    by_code = {row["indicator_code"]: row for row in indicator_rows}
    assert by_code["CECAD_HOUSEHOLDS_TOTAL"]["value"] == Decimal("240")
    assert by_code["CECAD_POVERTY_RATE"]["value"] == Decimal("25")
