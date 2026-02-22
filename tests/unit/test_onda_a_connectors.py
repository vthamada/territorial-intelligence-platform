from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.settings import Settings
from pipelines import (
    sejusp_public_safety,
    senatran_fleet,
    sidra_indicators,
    siops_health_finance,
    snis_sanitation,
)


def _build_settings() -> Settings:
    return Settings(
        municipality_ibge_code="3121605",
        database_url="postgresql+psycopg://postgres:postgres@localhost:5432/test_db",
    )


def test_sidra_extract_sidra_value_reads_numeric_from_rows() -> None:
    payload = [
        {"NC": "Valor"},
        {"D2N": "2024", "V": "49.493"},
    ]
    value, period = sidra_indicators._extract_sidra_value(payload, "2025")
    assert value == Decimal("49.493")
    assert period == "2024"


def test_sidra_extract_sidra_value_falls_back_to_requested_period_when_payload_period_is_label() -> None:
    payload = [
        {"NC": "Valor"},
        {"D2N": "Populacao residente estimada", "V": "49493"},
    ]
    value, period = sidra_indicators._extract_sidra_value(payload, "2025")
    assert value == Decimal("49493")
    assert period == "2025"


def test_sidra_connector_dry_run_uses_catalog_and_http_client(monkeypatch) -> None:
    catalog = [
        {
            "indicator_code": "SIDRA_POPULACAO_ESTIMADA",
            "indicator_name": "Populacao estimada (SIDRA)",
            "endpoint": (
                "https://apisidra.ibge.gov.br/values/t/6579/n6/"
                "{municipality_ibge_code}/v/9324/p/{reference_period}"
            ),
            "fallback_endpoint": (
                "https://apisidra.ibge.gov.br/values/t/6579/n6/"
                "{municipality_ibge_code}/v/9324/p/{fallback_period}"
            ),
            "unit": "pessoas",
            "category": "demografia",
        }
    ]

    class _FakeHttpClient:
        def get_json(self, _url: str):
            return [{"D2N": "2024", "V": "49493"}]

        def close(self) -> None:
            return None

    monkeypatch.setattr(sidra_indicators, "_load_indicators_catalog", lambda: catalog)
    monkeypatch.setattr(
        sidra_indicators,
        "_resolve_municipality_context",
        lambda _settings: ("00000000-0000-0000-0000-000000000000", "3121605"),
    )
    monkeypatch.setattr(
        sidra_indicators.HttpClient,
        "from_settings",
        lambda *args, **kwargs: _FakeHttpClient(),
    )

    result = sidra_indicators.run(reference_period="2025", dry_run=True, settings=_build_settings())

    assert result["job"] == sidra_indicators.JOB_NAME
    assert result["status"] == "success"
    assert result["rows_extracted"] == 1
    assert result["preview"]["catalog_size"] == 1
    assert result["preview"]["load_rows_preview"][0]["indicator_code"] == "SIDRA_POPULACAO_ESTIMADA"
    assert result["preview"]["load_rows_preview"][0]["reference_period"] == "2024"
    assert result["preview"]["load_rows_preview"][0]["value"] == "49493"


def test_senatran_resolve_municipality_row_by_code() -> None:
    dataframe = pd.DataFrame(
        [
            {"codigo_municipio": "3121605", "frota_total": "100", "motocicleta": "25"},
            {"codigo_municipio": "9999999", "frota_total": "50", "motocicleta": "10"},
        ]
    )
    row = senatran_fleet._resolve_municipality_row(
        dataframe,
        municipality_ibge_code="3121605",
        municipality_name="Diamantina",
    )
    assert row is not None
    assert row["codigo_municipio"] == "3121605"


def test_senatran_build_indicator_rows_uses_total_column() -> None:
    row = {"frota_total": "100", "motocicleta": "25"}
    indicators = senatran_fleet._build_indicator_rows(
        territory_id="00000000-0000-0000-0000-000000000000",
        reference_period="2025",
        municipality_row=row,
    )
    by_code = {item["indicator_code"]: item for item in indicators}
    assert by_code["SENATRAN_FROTA_TOTAL"]["value"] == Decimal("100")
    assert by_code["SENATRAN_FROTA_MOTOCICLETAS"]["value"] == Decimal("25")


def test_senatran_parse_numeric_handles_thousand_commas() -> None:
    assert senatran_fleet._parse_numeric("126,775,108") == Decimal("126775108")


def test_senatran_load_dataframe_from_bytes_handles_preface_rows() -> None:
    raw_bytes = (
        "Frota de veículos, por tipo e com placa, segundo os Municípios da Federação - JULHO/2025,,,,,\n"
        ",,\"126,775,108\",,,\n"
        "UF,MUNICIPIO,TOTAL,AUTOMOVEL,MOTOCICLETA,MOTONETA,ONIBUS,MICRO-ONIBUS\n"
        "MG,DIAMANTINA,\"1,234\",500,400,200,70,30\n"
    ).encode("utf-8")

    dataframe = senatran_fleet._load_dataframe_from_bytes(raw_bytes, suffix=".csv")

    assert len(dataframe) == 1
    assert dataframe.iloc[0]["MUNICIPIO"] == "DIAMANTINA"
    assert dataframe.iloc[0]["TOTAL"] == "1,234"


def test_senatran_discover_remote_resources_reads_year_csv_links() -> None:
    class _FakeHttpClient:
        def download_bytes(self, _url: str, **kwargs):  # noqa: ARG002
            payload = """
                <html><body>
                <a href="/transportes/pt-br/assuntos/transito/conteudo-Senatran/FrotaporMunicipioetipoAbril2024.csv">CSV 2024</a>
                <a href="/transportes/pt-br/assuntos/transito/conteudo-Senatran/FrotaporMunicipioetipoAbril2025.csv">CSV 2025</a>
                </body></html>
            """.encode("utf-8")
            return payload, "text/html"

    resources = senatran_fleet._discover_remote_resources(
        reference_period="2024",
        client=_FakeHttpClient(),
    )
    uris = [str(resource.get("uri", "")) for resource in resources]
    assert any(uri.endswith("Abril2024.csv") for uri in uris)
    assert all("2025" not in uri for uri in uris)


def test_senatran_manual_year_rank_prioritizes_reference_year() -> None:
    assert (
        senatran_fleet._manual_year_rank(
            Path("senatran_diamantina_2024.csv"),
            reference_period="2024",
        )
        == 0
    )
    assert (
        senatran_fleet._manual_year_rank(
            Path("senatran_diamantina.csv"),
            reference_period="2024",
        )
        == 1
    )
    assert (
        senatran_fleet._manual_year_rank(
            Path("senatran_diamantina_2025.csv"),
            reference_period="2024",
        )
        == 2
    )


def test_senatran_resolve_dataset_uses_discovered_remote_when_catalog_is_empty(monkeypatch) -> None:
    remote_csv_url = "https://example.test/FrotaporMunicipioetipoAbril2024.csv"

    class _FakeHttpClient:
        def download_bytes(self, url: str, **kwargs):  # noqa: ARG002
            if url != remote_csv_url:
                raise RuntimeError(f"Unexpected URL: {url}")
            payload = "codigo_municipio;frota_total\n3121605;222\n".encode("utf-8")
            return payload, "text/csv"

    monkeypatch.setattr(senatran_fleet, "_load_catalog", lambda: [])
    monkeypatch.setattr(
        senatran_fleet,
        "_discover_remote_resources",
        lambda **kwargs: [{"uri": remote_csv_url, "extension": ".csv"}],  # noqa: ARG005
    )

    dataset = senatran_fleet._resolve_dataset(
        settings=_build_settings(),
        reference_period="2024",
        client=_FakeHttpClient(),
    )

    assert dataset is not None
    dataframe, _raw_bytes, _suffix, source_type, source_uri, source_file_name, warnings = dataset
    assert source_type == "remote"
    assert source_uri == remote_csv_url
    assert source_file_name == "FrotaporMunicipioetipoAbril2024.csv"
    assert len(dataframe) == 1
    assert warnings == []


def test_senatran_resolve_dataset_skips_manual_year_mismatch(monkeypatch) -> None:
    class _FakeHttpClient:
        def download_bytes(self, _url: str, **kwargs):  # noqa: ARG002
            raise RuntimeError("No remote source should be requested in this test.")

    monkeypatch.setattr(senatran_fleet, "_load_catalog", lambda: [])
    monkeypatch.setattr(
        senatran_fleet,
        "_discover_remote_resources",
        lambda **kwargs: [],  # noqa: ARG005
    )
    monkeypatch.setattr(
        senatran_fleet,
        "_list_manual_candidates",
        lambda **kwargs: [Path("senatran_diamantina_2025.csv")],  # noqa: ARG005
    )

    dataset = senatran_fleet._resolve_dataset(
        settings=_build_settings(),
        reference_period="2024",
        client=_FakeHttpClient(),
    )

    assert dataset is None


def test_senatran_dry_run_uses_resolved_dataset(monkeypatch) -> None:
    dataframe = pd.DataFrame([{"codigo_municipio": "3121605", "frota_total": "120"}])

    class _FakeHttpClient:
        def close(self) -> None:
            return None

    monkeypatch.setattr(
        senatran_fleet,
        "_resolve_municipality_context",
        lambda _settings: ("00000000-0000-0000-0000-000000000000", "Diamantina", "3121605"),
    )
    monkeypatch.setattr(
        senatran_fleet,
        "_resolve_dataset",
        lambda **kwargs: (  # noqa: ARG005
            dataframe,
            b"raw",
            ".csv",
            "manual",
            "file:///tmp/frota.csv",
            "frota.csv",
            [],
        ),
    )
    monkeypatch.setattr(
        senatran_fleet.HttpClient,
        "from_settings",
        lambda *args, **kwargs: _FakeHttpClient(),
    )

    result = senatran_fleet.run(reference_period="2025", dry_run=True, settings=_build_settings())

    assert result["job"] == senatran_fleet.JOB_NAME
    assert result["status"] == "success"
    assert result["rows_extracted"] == 1
    assert result["preview"]["source_type"] == "manual"
    assert result["preview"]["indicators"][0]["indicator_code"] == "SENATRAN_FROTA_TOTAL"
    assert result["preview"]["indicators"][0]["value"] == "120"


def test_sejusp_resolve_municipality_row_by_code() -> None:
    dataframe = pd.DataFrame(
        [
            {"codigo_municipio": "3121605", "ocorrencias_total": "80", "roubos": "12"},
            {"codigo_municipio": "9999999", "ocorrencias_total": "30", "roubos": "3"},
        ]
    )
    row = sejusp_public_safety._resolve_municipality_row(
        dataframe,
        municipality_ibge_code="3121605",
        municipality_name="Diamantina",
    )
    assert row is not None
    assert row["codigo_municipio"] == "3121605"


def test_sejusp_build_indicator_rows_uses_total_column() -> None:
    row = {"ocorrencias_total": "80", "roubos": "12"}
    indicators = sejusp_public_safety._build_indicator_rows(
        territory_id="00000000-0000-0000-0000-000000000000",
        reference_period="2025",
        municipality_row=row,
    )
    by_code = {item["indicator_code"]: item for item in indicators}
    assert by_code["SEJUSP_OCORRENCIAS_TOTAL"]["value"] == Decimal("80")
    assert by_code["SEJUSP_ROUBOS"]["value"] == Decimal("12")


def test_sejusp_dry_run_uses_resolved_dataset(monkeypatch) -> None:
    dataframe = pd.DataFrame([{"codigo_municipio": "3121605", "ocorrencias_total": "90"}])

    class _FakeHttpClient:
        def close(self) -> None:
            return None

    monkeypatch.setattr(
        sejusp_public_safety,
        "_resolve_municipality_context",
        lambda _settings: ("00000000-0000-0000-0000-000000000000", "Diamantina", "3121605"),
    )
    monkeypatch.setattr(
        sejusp_public_safety,
        "_resolve_dataset",
        lambda **kwargs: (  # noqa: ARG005
            dataframe,
            b"raw",
            ".csv",
            "manual",
            "file:///tmp/sejusp.csv",
            "sejusp.csv",
            [],
        ),
    )
    monkeypatch.setattr(
        sejusp_public_safety.HttpClient,
        "from_settings",
        lambda *args, **kwargs: _FakeHttpClient(),
    )

    result = sejusp_public_safety.run(reference_period="2025", dry_run=True, settings=_build_settings())

    assert result["job"] == sejusp_public_safety.JOB_NAME
    assert result["status"] == "success"
    assert result["rows_extracted"] == 1
    assert result["preview"]["source_type"] == "manual"
    assert result["preview"]["indicators"][0]["indicator_code"] == "SEJUSP_OCORRENCIAS_TOTAL"
    assert result["preview"]["indicators"][0]["value"] == "90"


def test_siops_resolve_municipality_row_by_code() -> None:
    dataframe = pd.DataFrame(
        [
            {"codigo_municipio": "3121605", "despesa_total_saude": "1500000", "despesa_saude_per_capita": "300"},
            {"codigo_municipio": "9999999", "despesa_total_saude": "500000", "despesa_saude_per_capita": "200"},
        ]
    )
    row = siops_health_finance._resolve_municipality_row(
        dataframe,
        municipality_ibge_code="3121605",
        municipality_name="Diamantina",
    )
    assert row is not None
    assert row["codigo_municipio"] == "3121605"


def test_siops_build_indicator_rows_uses_total_column() -> None:
    row = {"despesa_total_saude": "1500000", "despesa_saude_per_capita": "300"}
    indicators = siops_health_finance._build_indicator_rows(
        territory_id="00000000-0000-0000-0000-000000000000",
        reference_period="2025",
        municipality_row=row,
    )
    by_code = {item["indicator_code"]: item for item in indicators}
    assert by_code["SIOPS_DESPESA_TOTAL_SAUDE"]["value"] == Decimal("1500000")
    assert by_code["SIOPS_DESPESA_SAUDE_PER_CAPITA"]["value"] == Decimal("300")


def test_siops_dry_run_uses_resolved_dataset(monkeypatch) -> None:
    dataframe = pd.DataFrame([{"codigo_municipio": "3121605", "despesa_total_saude": "1700000"}])

    class _FakeHttpClient:
        def close(self) -> None:
            return None

    monkeypatch.setattr(
        siops_health_finance,
        "_resolve_municipality_context",
        lambda _settings: ("00000000-0000-0000-0000-000000000000", "Diamantina", "3121605"),
    )
    monkeypatch.setattr(
        siops_health_finance,
        "_resolve_dataset",
        lambda **kwargs: (  # noqa: ARG005
            dataframe,
            b"raw",
            ".csv",
            "manual",
            "file:///tmp/siops.csv",
            "siops.csv",
            [],
        ),
    )
    monkeypatch.setattr(
        siops_health_finance.HttpClient,
        "from_settings",
        lambda *args, **kwargs: _FakeHttpClient(),
    )

    result = siops_health_finance.run(reference_period="2025", dry_run=True, settings=_build_settings())

    assert result["job"] == siops_health_finance.JOB_NAME
    assert result["status"] == "success"
    assert result["rows_extracted"] == 1
    assert result["preview"]["source_type"] == "manual"
    assert result["preview"]["indicators"][0]["indicator_code"] == "SIOPS_DESPESA_TOTAL_SAUDE"
    assert result["preview"]["indicators"][0]["value"] == "1700000"


def test_snis_resolve_municipality_row_by_code() -> None:
    dataframe = pd.DataFrame(
        [
            {"codigo_municipio": "3121605", "agua_atendimento_percentual": "92", "esgoto_atendimento_percentual": "70"},
            {"codigo_municipio": "9999999", "agua_atendimento_percentual": "85", "esgoto_atendimento_percentual": "40"},
        ]
    )
    row = snis_sanitation._resolve_municipality_row(
        dataframe,
        municipality_ibge_code="3121605",
        municipality_name="Diamantina",
    )
    assert row is not None
    assert row["codigo_municipio"] == "3121605"


def test_snis_build_indicator_rows_uses_percent_columns() -> None:
    row = {"agua_atendimento_percentual": "92", "esgoto_atendimento_percentual": "70"}
    indicators = snis_sanitation._build_indicator_rows(
        territory_id="00000000-0000-0000-0000-000000000000",
        reference_period="2025",
        municipality_row=row,
    )
    by_code = {item["indicator_code"]: item for item in indicators}
    assert by_code["SNIS_ATENDIMENTO_AGUA_PERCENTUAL"]["value"] == Decimal("92")
    assert by_code["SNIS_ATENDIMENTO_ESGOTO_PERCENTUAL"]["value"] == Decimal("70")


def test_snis_build_indicator_rows_ignores_nan_columns() -> None:
    row = {
        "agua_atendimento_percentual": float("nan"),
        "esgoto_atendimento_percentual": float("nan"),
        "perdas_agua_percentual": float("nan"),
        "coleta_residuos_percentual": "87.5",
    }
    indicators = snis_sanitation._build_indicator_rows(
        territory_id="00000000-0000-0000-0000-000000000000",
        reference_period="2025",
        municipality_row=row,
    )
    assert [item["indicator_code"] for item in indicators] == ["SNIS_COLETA_RESIDUOS_PERCENTUAL"]
    assert indicators[0]["value"] == Decimal("87.5")


def test_snis_dry_run_uses_resolved_dataset(monkeypatch) -> None:
    dataframe = pd.DataFrame([{"codigo_municipio": "3121605", "agua_atendimento_percentual": "93"}])

    class _FakeHttpClient:
        def close(self) -> None:
            return None

    monkeypatch.setattr(
        snis_sanitation,
        "_resolve_municipality_context",
        lambda _settings: ("00000000-0000-0000-0000-000000000000", "Diamantina", "3121605"),
    )
    monkeypatch.setattr(
        snis_sanitation,
        "_resolve_dataset",
        lambda **kwargs: (  # noqa: ARG005
            dataframe,
            b"raw",
            ".csv",
            "manual",
            "file:///tmp/snis.csv",
            "snis.csv",
            [],
        ),
    )
    monkeypatch.setattr(
        snis_sanitation.HttpClient,
        "from_settings",
        lambda *args, **kwargs: _FakeHttpClient(),
    )

    result = snis_sanitation.run(reference_period="2025", dry_run=True, settings=_build_settings())

    assert result["job"] == snis_sanitation.JOB_NAME
    assert result["status"] == "success"
    assert result["rows_extracted"] == 1
    assert result["preview"]["source_type"] == "manual"
    assert result["preview"]["indicators"][0]["indicator_code"] == "SNIS_ATENDIMENTO_AGUA_PERCENTUAL"
    assert result["preview"]["indicators"][0]["value"] == "93"
