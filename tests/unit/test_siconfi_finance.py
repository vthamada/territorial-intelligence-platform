from __future__ import annotations

from decimal import Decimal

from pipelines.siconfi_finance import (
    _build_indicator_rows,
    _candidate_years,
    _extract_dca_anexos,
    _normalize_indicator_code,
    _parse_reference_year,
)


def test_parse_reference_year_accepts_year_and_year_month() -> None:
    assert _parse_reference_year("2024") == 2024
    assert _parse_reference_year("2024-12") == 2024


def test_candidate_years_builds_descending_lookback() -> None:
    assert _candidate_years(2024, lookback_years=2) == [2024, 2023, 2022]


def test_extract_dca_anexos_filters_only_dca_prefixed_entries() -> None:
    payload = {
        "items": [
            {"demonstrativo": "DCA", "anexo": "DCA-Anexo I-AB"},
            {"demonstrativo": "DCA", "anexo": "Anexo I-AB"},
            {"demonstrativo": "QDCC", "anexo": "RGF-Anexo 01"},
            {"demonstrativo": "DCA", "anexo": "DCA-Anexo I-C"},
            {"demonstrativo": "DCA", "anexo": "DCA-Anexo I-AB"},
        ]
    }
    assert _extract_dca_anexos(payload) == ["DCA-Anexo I-AB", "DCA-Anexo I-C"]


def test_normalize_indicator_code_prefers_cod_conta() -> None:
    code = _normalize_indicator_code(
        cod_conta="P1.0.0.0.0.00.00",
        anexo="DCA-Anexo I-AB",
        conta="1.0.0.0.0.00.00 - Ativo",
    )
    assert code == "DCA_P1_0_0_0_0_00_00"


def test_build_indicator_rows_aggregates_values_by_indicator_and_period() -> None:
    items = [
        {
            "cod_conta": "P1.0.0.0.0.00.00",
            "conta": "1.0.0.0.0.00.00 - Ativo",
            "valor": "100,50",
            "exercicio": 2024,
        },
        {
            "cod_conta": "P1.0.0.0.0.00.00",
            "conta": "1.0.0.0.0.00.00 - Ativo",
            "valor": 49.5,
            "exercicio": 2024,
        },
    ]
    rows = _build_indicator_rows(
        territory_id="00000000-0000-0000-0000-000000000000",
        items=items,
        anexo="DCA-Anexo I-AB",
        fallback_reference_period="2024",
    )
    assert len(rows) == 1
    assert rows[0]["indicator_code"] == "DCA_P1_0_0_0_0_00_00"
    assert rows[0]["reference_period"] == "2024"
    assert rows[0]["value"] == Decimal("150.0")
