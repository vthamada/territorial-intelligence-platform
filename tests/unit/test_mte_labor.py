from __future__ import annotations

import os
import shutil
from decimal import Decimal
from uuid import uuid4
from types import SimpleNamespace
from pathlib import Path

import pandas as pd

from pipelines.mte_labor import (
    _build_indicator_rows,
    _compute_mte_metrics,
    _filter_municipality_rows,
    _list_bronze_cached_candidates,
    _load_bronze_cached_dataframe,
    _parse_reference_period,
    _parse_root_candidates,
    _select_best_ftp_file,
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


def test_compute_mte_metrics_derives_totals_from_saldo_movimentacao() -> None:
    df = pd.DataFrame(
        [
            {"saldomovimentacao": 1},
            {"saldomovimentacao": 1},
            {"saldomovimentacao": -1},
            {"saldomovimentacao": -1},
            {"saldomovimentacao": -1},
        ]
    )
    admissions, dismissals, balance = _compute_mte_metrics(df)
    assert admissions == Decimal("2")
    assert dismissals == Decimal("3")
    assert balance == Decimal("-1")


def test_select_best_ftp_file_prefers_latest_for_reference_year() -> None:
    paths = [
        "/pdet/microdados/NOVO CAGED/2024/CAGEDMOV202401.txt",
        "/pdet/microdados/NOVO CAGED/2024/CAGEDMOV202402.txt",
        "/pdet/microdados/NOVO CAGED/2023/CAGEDMOV202312.txt",
    ]
    selected = _select_best_ftp_file(paths, "2024")
    assert selected is not None
    assert selected.endswith("202402.txt")


def test_select_best_ftp_file_matches_reference_year_in_directory() -> None:
    paths = [
        "/pdet/microdados/NOVO CAGED/2024/cagedmov.txt",
        "/pdet/microdados/NOVO CAGED/2023/cagedmov202312.txt",
    ]
    selected = _select_best_ftp_file(paths, "2024")
    assert selected is not None
    assert "/2024/" in selected


def test_parse_root_candidates_uses_default_when_empty() -> None:
    assert _parse_root_candidates("") == (
        "/pdet/microdados/NOVO CAGED",
        "/pdet/microdados/NOVO_CAGED",
    )


def test_parse_root_candidates_splits_and_trims() -> None:
    parsed = _parse_root_candidates(" /a , /b,/c ")
    assert parsed == ("/a", "/b", "/c")


def test_list_bronze_cached_candidates_orders_by_mtime() -> None:
    root = Path("data") / f"mte_cache_test_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        bronze_root = root / "data" / "bronze"
        base = bronze_root / "mte" / "mte_novo_caged" / "2024"
        older = base / "extracted_at=2026-02-10T10-00-00Z" / "raw.csv"
        newer = base / "extracted_at=2026-02-10T11-00-00Z" / "raw.txt"
        older.parent.mkdir(parents=True, exist_ok=True)
        newer.parent.mkdir(parents=True, exist_ok=True)
        older.write_text("a;b\n1;2\n", encoding="utf-8")
        newer.write_text("a;b\n3;4\n", encoding="utf-8")
        os.utime(older, (1_700_000_000, 1_700_000_000))
        os.utime(newer, (1_700_000_060, 1_700_000_060))

        settings = SimpleNamespace(bronze_root=bronze_root)
        candidates = _list_bronze_cached_candidates(settings, "2024")

        assert [path.name for path in candidates] == ["raw.txt", "raw.csv"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_load_bronze_cached_dataframe_skips_invalid_candidate() -> None:
    root = Path("data") / f"mte_cache_test_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        invalid = root / "raw.zip"
        valid = root / "raw.csv"
        invalid.write_text("not-a-zip", encoding="utf-8")
        valid.write_text("municipio;uf;admissoes\nDiamantina;MG;10\n", encoding="utf-8")

        dataframe, source_uri, source_file_name, raw_bytes, suffix, warnings = _load_bronze_cached_dataframe(
            [invalid, valid]
        )

        assert dataframe is not None
        assert len(dataframe) == 1
        assert source_uri == valid.as_posix()
        assert source_file_name == "raw.csv"
        assert suffix == ".csv"
        assert raw_bytes is not None
        assert len(warnings) >= 1
    finally:
        shutil.rmtree(root, ignore_errors=True)
