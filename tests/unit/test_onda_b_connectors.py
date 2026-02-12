from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from app.settings import Settings
from pipelines import (
    ana_hydrology,
    aneel_energy,
    anatel_connectivity,
    inmet_climate,
    inpe_queimadas,
)
from pipelines.common import tabular_indicator_connector
from pipelines.common.tabular_indicator_connector import IndicatorSpec, _build_indicator_rows


def _build_settings() -> Settings:
    return Settings(
        municipality_ibge_code="3121605",
        database_url="postgresql+psycopg://postgres:postgres@localhost:5432/test_db",
    )


def test_build_indicator_rows_applies_aggregators() -> None:
    municipality_rows = [
        {
            "temp_media": "20",
            "chuva_mm": "10",
            "umidade_media": "80",
        },
        {
            "temp_media": "24",
            "chuva_mm": "20",
            "umidade_media": "70",
        },
    ]
    specs = (
        IndicatorSpec(
            code="RAIN",
            name="Rain",
            unit="mm",
            category="clima",
            candidates=("chuva_mm",),
            aggregator="sum",
        ),
        IndicatorSpec(
            code="TEMP",
            name="Temperature",
            unit="C",
            category="clima",
            candidates=("temp_media",),
            aggregator="avg",
        ),
        IndicatorSpec(
            code="HUM",
            name="Humidity",
            unit="percent",
            category="clima",
            candidates=("umidade_media",),
            aggregator="max",
        ),
    )

    rows = _build_indicator_rows(
        territory_id="00000000-0000-0000-0000-000000000000",
        reference_period="2025",
        municipality_rows=municipality_rows,
        source="INMET",
        fact_dataset_name="inmet",
        indicator_specs=specs,
    )
    by_code = {item["indicator_code"]: item for item in rows}

    assert by_code["RAIN"]["value"] == Decimal("30")
    assert by_code["TEMP"]["value"] == Decimal("22")
    assert by_code["HUM"]["value"] == Decimal("80")


class _FakeHttpClient:
    def close(self) -> None:
        return None


@pytest.mark.parametrize(
    ("module", "dataframe", "expected_indicator"),
    [
        (
            inmet_climate,
            pd.DataFrame(
                [{"codigo_municipio": "3121605", "precipitacao_total_mm": "100", "temperatura_media_c": "22"}]
            ),
            "INMET_PRECIPITACAO_TOTAL_MM",
        ),
        (
            inpe_queimadas,
            pd.DataFrame([{"codigo_municipio": "3121605", "focos_total": "5"}]),
            "INPE_FOCOS_QUEIMADAS_TOTAL",
        ),
        (
            ana_hydrology,
            pd.DataFrame([{"codigo_municipio": "3121605", "vazao_media_m3s": "1.25"}]),
            "ANA_VAZAO_MEDIA_M3S",
        ),
        (
            anatel_connectivity,
            pd.DataFrame([{"codigo_municipio": "3121605", "servico": "Banda Larga Fixa", "acessos": "800"}]),
            "ANATEL_ACESSOS_BANDA_LARGA_FIXA",
        ),
        (
            aneel_energy,
            pd.DataFrame([{"codigo_municipio": "3121605", "consumo_total_mwh": "1234"}]),
            "ANEEL_CONSUMO_TOTAL_MWH",
        ),
    ],
)
def test_onda_b_connector_dry_run_uses_resolved_dataset(
    monkeypatch: pytest.MonkeyPatch,
    module: Any,
    dataframe: pd.DataFrame,
    expected_indicator: str,
) -> None:
    monkeypatch.setattr(
        tabular_indicator_connector,
        "_resolve_municipality_context",
        lambda _settings: ("00000000-0000-0000-0000-000000000000", "Diamantina", "3121605"),
    )
    monkeypatch.setattr(
        tabular_indicator_connector,
        "_resolve_dataset",
        lambda **kwargs: (  # noqa: ARG005
            dataframe,
            b"raw",
            ".csv",
            "manual",
            "file:///tmp/source.csv",
            "source.csv",
            [],
        ),
    )
    monkeypatch.setattr(
        tabular_indicator_connector.HttpClient,
        "from_settings",
        lambda *args, **kwargs: _FakeHttpClient(),
    )

    result = module.run(reference_period="2025", dry_run=True, settings=_build_settings())

    assert result["status"] == "success"
    assert result["rows_extracted"] == 1
    assert result["preview"]["source_type"] == "manual"
    assert any(item["indicator_code"] == expected_indicator for item in result["preview"]["indicators"])


def test_resolve_municipality_rows_uses_source_filename_hint_when_columns_are_missing() -> None:
    dataframe = pd.DataFrame(
        [
            {"precipitacao_total_mm": "10,0", "temperatura_media_c": "20"},
            {"precipitacao_total_mm": "5,0", "temperatura_media_c": "22"},
        ]
    )

    rows = tabular_indicator_connector._resolve_municipality_rows(
        dataframe,
        municipality_ibge_code="3121605",
        municipality_name="Diamantina",
        code_columns=("codigo_municipio",),
        name_columns=("municipio",),
        source_file_name="INMET_SE_MG_A537_DIAMANTINA_01-01-2025_A_31-12-2025.CSV",
    )

    assert len(rows) == 2


def test_build_indicator_rows_applies_row_filters() -> None:
    municipality_rows = [
        {"servico": "Banda Larga Fixa", "acessos": "100"},
        {"servico": "Telefonia Móvel", "acessos": "300"},
    ]
    specs = (
        IndicatorSpec(
            code="FIXA",
            name="Fixa",
            unit="count",
            category="conectividade",
            candidates=("acessos",),
            aggregator="sum",
            row_filters={"servico": ("banda larga fixa",)},
        ),
        IndicatorSpec(
            code="MOVEL",
            name="Movel",
            unit="count",
            category="conectividade",
            candidates=("acessos",),
            aggregator="sum",
            row_filters={"servico": ("telefonia movel",)},
        ),
    )

    rows = _build_indicator_rows(
        territory_id="00000000-0000-0000-0000-000000000000",
        reference_period="2025",
        municipality_rows=municipality_rows,
        source="ANATEL",
        fact_dataset_name="anatel",
        indicator_specs=specs,
    )
    by_code = {item["indicator_code"]: item for item in rows}
    assert by_code["FIXA"]["value"] == Decimal("100")
    assert by_code["MOVEL"]["value"] == Decimal("300")


def test_load_dataframe_from_bytes_supports_arcgis_features_payload() -> None:
    payload = (
        '{"features":[{"attributes":{"codigo_municipio":"3121605","vazao_media_m3s":"2,5"}}]}'
    ).encode("utf-8")

    dataframe = tabular_indicator_connector._load_dataframe_from_bytes(payload, suffix=".json")

    assert "codigo_municipio" in dataframe.columns
    assert "vazao_media_m3s" in dataframe.columns
    assert str(dataframe.iloc[0]["codigo_municipio"]) == "3121605"


def test_run_tabular_connector_uses_manual_fallback_when_remote_has_no_indicator_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manual_dir = Path("data/manual/inpe_queimadas")
    manual_dir.mkdir(parents=True, exist_ok=True)
    manual_file = manual_dir / "_pytest_inpe_queimadas_diamantina_2025.csv"
    manual_file.write_text(
        "codigo_municipio;municipio;focos_total\n3121605;Diamantina;91\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        tabular_indicator_connector,
        "_resolve_municipality_context",
        lambda _settings: ("00000000-0000-0000-0000-000000000000", "Diamantina", "3121605"),
    )
    monkeypatch.setattr(
        tabular_indicator_connector,
        "_resolve_dataset",
        lambda **kwargs: (  # noqa: ARG005
            pd.DataFrame([{"codigo_municipio": "3121605", "municipio": "Diamantina"}]),
            b"remote",
            ".csv",
            "remote",
            "https://example.org/remote.csv",
            "remote.csv",
            [],
        ),
    )
    monkeypatch.setattr(
        tabular_indicator_connector,
        "_list_manual_candidates",
        lambda _path: [manual_file],
    )
    monkeypatch.setattr(
        tabular_indicator_connector,
        "_load_dataframe_from_bytes",
        lambda *_args, **_kwargs: pd.read_csv(manual_file, sep=";"),
    )
    monkeypatch.setattr(
        tabular_indicator_connector.HttpClient,
        "from_settings",
        lambda *args, **kwargs: _FakeHttpClient(),
    )

    try:
        result = inpe_queimadas.run(reference_period="2025", dry_run=True, settings=_build_settings())

        assert result["status"] == "success"
        assert result["preview"]["source_type"] == "manual"
        assert any("manual fallback" in warning for warning in result["warnings"])
    finally:
        manual_file.unlink(missing_ok=True)
