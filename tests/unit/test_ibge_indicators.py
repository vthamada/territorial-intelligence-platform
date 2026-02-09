from __future__ import annotations

from decimal import Decimal

from pipelines.ibge_indicators import _extract_path, _parse_numeric, _resolve_indicator_value


def test_extract_path_reads_nested_json() -> None:
    payload = [{"resultados": [{"series": [{"serie": {"2024": "123"}}]}]}]
    assert _extract_path(payload, "0.resultados.0.series.0.serie.2024") == "123"


def test_parse_numeric_handles_common_ibge_formats() -> None:
    assert _parse_numeric("12.345,67") == Decimal("12345.67")
    assert _parse_numeric("49493") == Decimal("49493")
    assert _parse_numeric("...") is None


def test_resolve_indicator_value_falls_back_to_latest_period() -> None:
    payload = [{"resultados": [{"series": [{"serie": {"2022": "10", "2023": "20"}}]}]}]
    value, period, warning = _resolve_indicator_value(
        payload=payload,
        requested_period="2026",
        value_path_template="0.resultados.0.series.0.serie.{year}",
    )
    assert value == Decimal("20")
    assert period == "2023"
    assert warning is not None
