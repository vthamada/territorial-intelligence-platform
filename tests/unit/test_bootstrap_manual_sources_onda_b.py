from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest


def _load_bootstrap_module():
    module_path = Path("scripts/bootstrap_manual_sources.py")
    spec = importlib.util.spec_from_file_location("bootstrap_manual_sources", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_municipality_subset_matches_by_code_or_name() -> None:
    module = _load_bootstrap_module()
    dataframe = pd.DataFrame(
        [
            {"codigo_municipio": "3121605", "municipio": "Diamantina", "valor": "10"},
            {"codigo_municipio": "9999999", "municipio": "Outra Cidade", "valor": "20"},
            {"codigo_municipio": "", "municipio": "Diamantina", "valor": "30"},
        ]
    )

    rows = module._resolve_municipality_subset(
        dataframe,
        municipality_ibge_code="3121605",
        municipality_name="Diamantina",
    )

    assert len(rows) == 2
    assert sorted(rows["valor"].astype(str).tolist()) == ["10", "30"]


def test_resolve_municipality_subset_supports_cdmun_and_nmmun_columns() -> None:
    module = _load_bootstrap_module()
    dataframe = pd.DataFrame(
        [
            {"CDMUN": "3121605", "NMMUN": "Diamantina", "VZTOTM3S": "0.40"},
            {"CDMUN": "9999999", "NMMUN": "Outro", "VZTOTM3S": "0.10"},
        ]
    )

    rows = module._resolve_municipality_subset(
        dataframe,
        municipality_ibge_code="3121605",
        municipality_name="Diamantina",
    )

    assert len(rows) == 1
    assert str(rows.iloc[0]["vztotm3s"]) == "0.40"


def test_aggregate_metric_from_rows_supports_sum_avg_and_max() -> None:
    module = _load_bootstrap_module()
    rows = pd.DataFrame(
        [
            {"chuva_mm": "10,5", "temperatura_media": "20", "risco": "3"},
            {"chuva_mm": "5,0", "temperatura_media": "24", "risco": "4"},
        ]
    )

    chuva = module._aggregate_metric_from_rows(rows, aliases=["chuva_mm"], mode="sum")
    temp = module._aggregate_metric_from_rows(rows, aliases=["temperatura_media"], mode="avg")
    risco = module._aggregate_metric_from_rows(rows, aliases=["risco"], mode="max")

    assert chuva == 15.5
    assert temp == 22.0
    assert risco == 4.0


def test_aggregate_metric_from_rows_supports_count_mode() -> None:
    module = _load_bootstrap_module()
    rows = pd.DataFrame(
        [
            {"foco_id": "abc"},
            {"foco_id": "def"},
            {"foco_id": ""},
        ]
    )

    focos = module._aggregate_metric_from_rows(rows, aliases=["foco_id"], mode="count")

    assert focos == 2.0


def test_resolve_municipality_subset_falls_back_to_source_filename_hint() -> None:
    module = _load_bootstrap_module()
    dataframe = pd.DataFrame(
        [
            {"precipitacao_total_mm": "10,0", "temperatura_media_c": "20"},
            {"precipitacao_total_mm": "5,0", "temperatura_media_c": "22"},
        ]
    )

    rows = module._resolve_municipality_subset(
        dataframe,
        municipality_ibge_code="3121605",
        municipality_name="Diamantina",
        source_file_name="INMET_SE_MG_A537_DIAMANTINA_01-01-2025_A_31-12-2025.CSV",
    )

    assert len(rows) == 2


def test_filter_rows_by_reference_year_keeps_matching_rows() -> None:
    module = _load_bootstrap_module()
    rows = pd.DataFrame(
        [
            {"ano": "2024", "valor": "10"},
            {"ano": "2025", "valor": "20"},
            {"ano": "2025", "valor": "30"},
        ]
    )

    filtered = module._filter_rows_by_reference_year(
        rows,
        reference_year="2025",
        year_columns=("ano",),
    )

    assert filtered["valor"].astype(str).tolist() == ["20", "30"]


def test_aggregate_metric_from_rows_applies_filters() -> None:
    module = _load_bootstrap_module()
    rows = pd.DataFrame(
        [
            {"servico": "Banda Larga Fixa", "acessos": "100"},
            {"servico": "Telefonia Móvel", "acessos": "300"},
        ]
    )

    fixa = module._aggregate_metric_from_rows(
        rows,
        aliases=["acessos"],
        mode="sum",
        filters={"servico": ("banda larga fixa",)},
    )

    assert fixa == 100.0


def test_aggregate_metric_from_rows_supports_ana_vazao_aliases() -> None:
    module = _load_bootstrap_module()
    rows = pd.DataFrame([{"VZTOTM3S": "0.405273"}])

    value = module._aggregate_metric_from_rows(
        rows,
        aliases=["vazao_media_m3s", "vztotm3s"],
        mode="avg",
    )

    assert value == 0.405273


def test_bootstrap_tabular_catalog_source_sanitizes_query_filename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_bootstrap_module()
    raw_csv = "codigo_municipio;municipio;valor\n3121605;Diamantina;1\n".encode("utf-8")

    class _FakeResponse:
        content = raw_csv

        @staticmethod
        def raise_for_status() -> None:
            return None

    class _FakeSession:
        @staticmethod
        def get(_uri: str, timeout: int = 120):  # noqa: ARG004
            return _FakeResponse()

    monkeypatch.setattr(module, "_session", lambda: _FakeSession())
    monkeypatch.setattr(
        module,
        "_load_catalog_resources",
        lambda _path: [
            {
                "uri": "https://hub.arcgis.com/api/download/v1/items/test/csv?layers=18",
                "extension": ".csv",
            }
        ],
    )

    output_filename = "_pytest_bootstrap_ana.csv"
    result = module._bootstrap_tabular_catalog_source(
        source="ANA",
        catalog_path=Path("configs/ana_hydrology_catalog.yml"),
        raw_subdir="ana",
        manual_subdir="ana",
        output_filename=output_filename,
        reference_year="2025",
        municipality_name="Diamantina",
        municipality_ibge_code="3121605",
        metric_specs=[{"column": "valor_total", "aliases": ["valor"], "mode": "sum"}],
    )

    try:
        assert result.status == "ok"
        assert result.output_file is not None
        assert result.details is not None
        assert str(result.details.get("raw_file", "")).endswith("csv.csv")
    finally:
        output_path = Path("data/manual/ana") / output_filename
        output_path.unlink(missing_ok=True)
        raw_path = Path("data/raw/bootstrap/ana/csv.csv")
        raw_path.unlink(missing_ok=True)
