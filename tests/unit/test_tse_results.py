from __future__ import annotations

import io
import zipfile

from pipelines.tse_results import (
    _build_result_checks,
    _extract_rows_from_zip,
    _normalize_text,
    _normalize_zone,
    _pick_results_resource,
)


def test_normalize_text_handles_accents() -> None:
    assert _normalize_text("APURAÇÃO") == "apuracao"


def test_pick_results_resource_prefers_detalhe_munzona_zip() -> None:
    resources = [
        {
            "name": "Votação nominal por município e zona",
            "url": "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/x.zip",
        },
        {
            "name": "Detalhe da apuração por município e zona",
            "url": "https://cdn.tse.jus.br/estatistica/sead/odsele/detalhe_votacao_munzona/y.zip",
        },
    ]
    selected = _pick_results_resource(resources)
    assert selected is not None
    assert "detalhe_votacao_munzona" in selected["url"]


def test_normalize_zone() -> None:
    assert _normalize_zone("0012") == "12"
    assert _normalize_zone("12.0") == "12"
    assert _normalize_zone("Zona 14") == "14"
    assert _normalize_zone(None) is None
    assert _normalize_zone("") is None


def _zip_with_csv(csv_name: str, csv_content: str) -> bytes:
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(csv_name, csv_content.encode("latin1"))
    return raw.getvalue()


def test_extract_rows_from_zip_parses_zone_when_column_exists() -> None:
    csv_content = (
        "ANO_ELEICAO;NR_TURNO;SG_UF;NM_MUNICIPIO;DS_CARGO;NR_ZONA;NR_SECAO;"
        "QT_COMPARECIMENTO;QT_ABSTENCOES;QT_VOTOS;QT_TOTAL_VOTOS_VALIDOS;QT_VOTOS_BRANCOS;QT_TOTAL_VOTOS_NULOS\n"
        "2024;1;MG;Diamantina;Prefeito;0012;0034;100;20;120;110;5;5\n"
    )
    zip_bytes = _zip_with_csv("detalhe_mg.csv", csv_content)

    rows, parse_info = _extract_rows_from_zip(
        zip_bytes=zip_bytes,
        municipality_name="Diamantina",
        uf="MG",
    )

    assert rows
    assert rows[0]["election_year"] == 2024
    assert rows[0]["tse_zone"] == "12"
    assert rows[0]["tse_section"] == "34"
    assert parse_info["zone_column"] == "NR_ZONA"
    assert parse_info["section_column"] == "NR_SECAO"
    assert parse_info["polling_place_column"] is None
    assert parse_info["zones_detected"] == ["12"]
    assert parse_info["sections_detected"] == ["12/34"]
    assert parse_info["polling_places_detected"] == 0


def test_extract_rows_from_zip_handles_missing_zone_column() -> None:
    csv_content = (
        "ANO_ELEICAO;NR_TURNO;SG_UF;NM_MUNICIPIO;DS_CARGO;"
        "QT_COMPARECIMENTO;QT_ABSTENCOES;QT_VOTOS;QT_TOTAL_VOTOS_VALIDOS;QT_VOTOS_BRANCOS;QT_TOTAL_VOTOS_NULOS\n"
        "2024;1;MG;Diamantina;Prefeito;100;20;120;110;5;5\n"
    )
    zip_bytes = _zip_with_csv("detalhe_mg.csv", csv_content)

    rows, parse_info = _extract_rows_from_zip(
        zip_bytes=zip_bytes,
        municipality_name="Diamantina",
        uf="MG",
    )

    assert rows
    assert rows[0]["tse_zone"] is None
    assert rows[0]["tse_section"] is None
    assert parse_info["zone_column"] is None
    assert parse_info["section_column"] is None
    assert parse_info["polling_place_column"] is None
    assert parse_info["zones_detected"] == []
    assert parse_info["sections_detected"] == []
    assert parse_info["polling_places_detected"] == 0


def test_extract_rows_from_zip_collects_polling_place_name() -> None:
    csv_content = (
        "ANO_ELEICAO;NR_TURNO;SG_UF;NM_MUNICIPIO;DS_CARGO;NR_ZONA;NR_SECAO;NM_LOCAL_VOTACAO;"
        "QT_COMPARECIMENTO;QT_ABSTENCOES;QT_VOTOS;QT_TOTAL_VOTOS_VALIDOS;QT_VOTOS_BRANCOS;QT_TOTAL_VOTOS_NULOS\n"
        "2024;1;MG;Diamantina;Prefeito;0012;0034;Escola Estadual A;100;20;120;110;5;5\n"
    )
    zip_bytes = _zip_with_csv("detalhe_mg.csv", csv_content)

    rows, parse_info = _extract_rows_from_zip(
        zip_bytes=zip_bytes,
        municipality_name="Diamantina",
        uf="MG",
    )

    assert rows
    assert rows[0]["polling_place_name"] == "Escola Estadual A"
    assert parse_info["polling_place_column"] == "NM_LOCAL_VOTACAO"
    assert parse_info["polling_places_detected"] == 1


def test_build_result_checks_with_detected_and_upserted_keys() -> None:
    checks = _build_result_checks(
        package_id="pkg-123",
        parsed_rows_count=12,
        rows_written=12,
        zones_detected=3,
        sections_detected=9,
        polling_places_detected=6,
        zones_upserted=3,
        sections_upserted=9,
    )
    checks_by_name = {check["name"]: check for check in checks}

    assert checks_by_name["ckan_package_resolved"]["status"] == "pass"
    assert checks_by_name["results_rows_extracted"]["observed_value"] == 12
    assert checks_by_name["results_rows_loaded"]["observed_value"] == 12
    assert checks_by_name["electoral_zone_keys_detected"]["status"] == "pass"
    assert checks_by_name["electoral_section_keys_detected"]["status"] == "pass"
    assert checks_by_name["electoral_polling_places_detected"]["status"] == "pass"
    assert checks_by_name["electoral_zone_rows_detected"]["status"] == "pass"
    assert checks_by_name["electoral_section_rows_detected"]["status"] == "pass"


def test_build_result_checks_warns_when_no_keys_or_rows() -> None:
    checks = _build_result_checks(
        package_id="pkg-empty",
        parsed_rows_count=0,
        rows_written=0,
        zones_detected=0,
        sections_detected=0,
        polling_places_detected=0,
        zones_upserted=0,
        sections_upserted=0,
    )
    checks_by_name = {check["name"]: check for check in checks}

    assert checks_by_name["results_rows_extracted"]["status"] == "warn"
    assert checks_by_name["results_rows_loaded"]["status"] == "warn"
    assert checks_by_name["electoral_zone_keys_detected"]["status"] == "warn"
    assert checks_by_name["electoral_section_keys_detected"]["status"] == "warn"
    assert checks_by_name["electoral_polling_places_detected"]["status"] == "warn"
    assert checks_by_name["electoral_zone_rows_detected"]["status"] == "warn"
    assert checks_by_name["electoral_section_rows_detected"]["status"] == "warn"
