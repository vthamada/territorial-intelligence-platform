from __future__ import annotations

from decimal import Decimal

from pipelines.portal_transparencia import (
    _build_metrics,
    _extract_items,
    _month_tokens,
    _parse_reference_year,
    _sum_field,
)


def test_parse_reference_year_accepts_year_and_year_month() -> None:
    assert _parse_reference_year("2025") == 2025
    assert _parse_reference_year("2025-06") == 2025


def test_month_tokens_builds_12_month_sequence() -> None:
    assert _month_tokens(2025)[0] == "202501"
    assert _month_tokens(2025)[-1] == "202512"
    assert len(_month_tokens(2025)) == 12


def test_extract_items_supports_list_and_items_wrapper() -> None:
    payload_list = [{"a": 1}, {"a": 2}]
    payload_items = {"items": [{"a": 3}, {"a": 4}]}

    assert len(_extract_items(payload_list)) == 2
    assert len(_extract_items(payload_items)) == 2


def test_sum_field_parses_mixed_number_formats() -> None:
    rows = [{"valor": "1.000,50"}, {"valor": "200.25"}, {"valor": 10}, {"valor": None}]
    assert _sum_field(rows, "valor") == Decimal("1210.75")


def test_build_metrics_aggregates_expected_portal_indicators() -> None:
    metrics = _build_metrics(
        rows_by_key={
            "bpc": [{"valor": "100,00", "quantidadeBeneficiados": 2}],
            "bolsa": [{"valor": "250", "quantidadeBeneficiados": 5}],
            "novo_bolsa": [
                {"valorSaque": "300,00", "nis": "123"},
                {"valorSaque": "50", "cpfFormatado": "111.222.333-44"},
            ],
            "auxilio_brasil": [{"valor": "80", "quantidadeBeneficiados": 1}],
            "auxilio_emergencial": [{"valor": "70", "quantidadeBeneficiados": 1}],
            "peti": [{"valor": "10"}],
            "safra": [{"valor": "20"}],
            "defeso": [{"valor": "30"}],
            "recursos": [{"valor": "400"}],
            "convenios": [{"valor": "500", "valorLiberado": "150"}],
            "renuncias": [{"valorRenunciado": "60"}],
            "covid_transferencias": [{"valor": "90"}],
        }
    )
    by_code = {item.code: item for item in metrics}

    assert by_code["PT_BPC_VALOR_TOTAL"].value == Decimal("100")
    assert by_code["PT_BOLSA_FAMILIA_VALOR_TOTAL"].value == Decimal("250")
    assert by_code["PT_NOVO_BOLSA_FAMILIA_VALOR_TOTAL"].value == Decimal("350")
    assert by_code["PT_NOVO_BOLSA_FAMILIA_BENEFICIARIOS_UNICOS"].value == Decimal("2")
    assert by_code["PT_RECURSOS_RECEBIDOS_VALOR_TOTAL"].value == Decimal("400")
    assert by_code["PT_CONVENIOS_VALOR_LIBERADO_TOTAL"].value == Decimal("150")
    assert by_code["PT_RENUNCIAS_VALOR_TOTAL"].value == Decimal("60")
