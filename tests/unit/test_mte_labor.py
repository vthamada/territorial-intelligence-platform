from __future__ import annotations

from decimal import Decimal

import pandas as pd

from pipelines.mte_labor import (
    _build_indicator_rows,
    _filter_municipality_rows,
    _parse_reference_period,
)


def test_parse_reference_period_accepts_year_and_year_month() -> None:
    assert _parse_reference_period("2024") == "2024"
    assert _parse_reference_period("2024-12") == "2024"


def test_filter_municipality_rows_prefers_ibge_code_match() -> None:
    df = pd.DataFrame(
        [
            {"Codigo Municipio": "3121606", "Admissoes": "10"},
            {"Codigo Municipio": "9999999", "Admissoes": "20"},
        ]
    )
    filtered = _filter_municipality_rows(
        df,
        municipality_name="Diamantina",
        municipality_ibge_code="3121606",
    )
    assert len(filtered) == 1
    assert str(filtered.iloc[0]["codigo_municipio"]) == "3121606"


def test_filter_municipality_rows_falls_back_to_city_name_and_uf() -> None:
    df = pd.DataFrame(
        [
            {"Municipio": "Diamantina", "UF": "BA", "Admissoes": "10"},
            {"Municipio": "Diamantina", "UF": "MG", "Admissoes": "30"},
            {"Municipio": "Outro", "UF": "MG", "Admissoes": "99"},
        ]
    )
    filtered = _filter_municipality_rows(
        df,
        municipality_name="Diamantina",
        municipality_ibge_code="3121606",
    )
    assert len(filtered) == 1
    assert filtered.iloc[0]["uf"] == "MG"


def test_build_indicator_rows_aggregates_manual_metrics() -> None:
    filtered_df = pd.DataFrame(
        [
            {"admissoes": "1.000", "desligamentos": "500", "saldo": "500"},
            {"admissoes": "200", "desligamentos": "50", "saldo": "150"},
        ]
    )
    rows = _build_indicator_rows(
        territory_id="00000000-0000-0000-0000-000000000000",
        reference_period="2024",
        filtered_df=filtered_df,
    )
    by_code = {row["indicator_code"]: row for row in rows}
    assert by_code["MTE_NOVO_CAGED_ADMISSOES_TOTAL"]["value"] == Decimal("1200")
    assert by_code["MTE_NOVO_CAGED_DESLIGAMENTOS_TOTAL"]["value"] == Decimal("550")
    assert by_code["MTE_NOVO_CAGED_SALDO_TOTAL"]["value"] == Decimal("650")
    assert by_code["MTE_NOVO_CAGED_REGISTROS_TOTAL"]["value"] == Decimal("2")

