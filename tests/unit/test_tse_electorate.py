from __future__ import annotations

import io
import zipfile

import pytest

from pipelines.tse_electorate import (
    _extract_local_voting_metadata_from_zip,
    _extract_rows_from_zip,
    _extract_section_rows_from_zip,
    _normalize_text,
    _pick_electorate_resource,
    _pick_electorate_section_resource,
    _pick_local_voting_resource,
    _safe_optional_int,
    _safe_optional_text,
    _resolve_electorate_package,
    _resolve_electorate_columns,
    _safe_dimension,
)


def test_normalize_text_removes_accents_and_case() -> None:
    assert _normalize_text("Diamantina") == "diamantina"
    assert _normalize_text("IBIRAÇU") == "ibiracu"


def test_safe_dimension_uses_fallback_for_empty_values() -> None:
    assert _safe_dimension(None) == "NAO_INFORMADO"
    assert _safe_dimension("") == "NAO_INFORMADO"
    assert _safe_dimension("MASCULINO") == "MASCULINO"


def test_safe_optional_metadata_sanitizes_nan_values() -> None:
    assert _safe_optional_text(None) is None
    assert _safe_optional_text(float("nan")) is None
    assert _safe_optional_text("nan") is None
    assert _safe_optional_text(" Escola A ") == "Escola A"

    assert _safe_optional_int(None) is None
    assert _safe_optional_int(float("nan")) is None
    assert _safe_optional_int("1465") == 1465


def test_pick_electorate_resource_prefers_perfil_eleitorado_zip() -> None:
    resources = [
        {
            "name": "Eleitorado por local de votação - 2024",
            "url": "https://cdn.tse.jus.br/estatistica/sead/odsele/eleitorado_locais_votacao/x.zip",
        },
        {
            "name": "Eleitorado - 2024",
            "url": "https://cdn.tse.jus.br/estatistica/sead/odsele/perfil_eleitorado/perfil_eleitorado_2024.zip",
        },
    ]
    selected = _pick_electorate_resource(resources)
    assert selected is not None
    assert "perfil_eleitorado" in selected["url"]


def test_pick_section_and_local_resources_for_requested_year_and_uf() -> None:
    resources = [
        {
            "name": "Perfil do eleitorado por seção eleitoral 2024 - MG",
            "url": "https://cdn.tse.jus.br/estatistica/sead/odsele/perfil_eleitor_secao/perfil_eleitor_secao_2024_MG.zip",
        },
        {
            "name": "Eleitorado por local de votação - 2024",
            "url": "https://cdn.tse.jus.br/estatistica/sead/odsele/eleitorado_local_votacao/eleitorado_local_votacao_2024.zip",
        },
    ]

    section_resource = _pick_electorate_section_resource(resources, reference_year=2024, uf="MG")
    assert section_resource is not None
    assert "perfil_eleitor_secao_2024_mg.zip" in section_resource["url"].lower()

    local_resource = _pick_local_voting_resource(resources, reference_year=2024)
    assert local_resource is not None
    assert "eleitorado_local_votacao_2024.zip" in local_resource["url"].lower()


def test_resolve_electorate_columns_accepts_new_aliases() -> None:
    columns = [
        "ANO_ELEICAO",
        "SG_UF",
        "NM_MUNICIPIO",
        "DS_GENERO",
        "DS_FAIXA_ETARIA",
        "DS_GRAU_INSTRUCAO",
        "QT_ELEITORES",
    ]
    resolved = _resolve_electorate_columns(columns)
    assert resolved["DS_GRAU_ESCOLARIDADE"] == "DS_GRAU_INSTRUCAO"
    assert resolved["QT_ELEITORES_PERFIL"] == "QT_ELEITORES"


def test_resolve_electorate_columns_keeps_zone_optional() -> None:
    columns = [
        "ANO_ELEICAO",
        "SG_UF",
        "NM_MUNICIPIO",
        "DS_GENERO",
        "DS_FAIXA_ETARIA",
        "DS_GRAU_ESCOLARIDADE",
        "QT_ELEITORES_PERFIL",
    ]
    resolved = _resolve_electorate_columns(columns)
    assert "NR_ZONA" not in resolved


def test_resolve_electorate_columns_raises_when_required_missing() -> None:
    columns = ["ANO_ELEICAO", "SG_UF"]
    with pytest.raises(ValueError):
        _resolve_electorate_columns(columns)


def test_resolve_electorate_package_prefers_requested_year(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_get(_client, _base_url: str, package_id: str):
        if package_id == "eleitorado-2024":
            return {"id": package_id}
        return None

    monkeypatch.setattr("pipelines.tse_electorate._ckan_get_package", _fake_get)

    package, package_id, warnings = _resolve_electorate_package(
        client=object(),  # type: ignore[arg-type]
        base_url="https://example.test",
        reference_year=2024,
    )

    assert package is not None
    assert package_id == "eleitorado-2024"
    assert warnings == []


def test_resolve_electorate_package_falls_back_to_historical_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_get(_client, _base_url: str, package_id: str):
        if package_id == "eleitorado-2022":
            return {"id": package_id}
        return None

    monkeypatch.setattr("pipelines.tse_electorate._ckan_get_package", _fake_get)

    package, package_id, warnings = _resolve_electorate_package(
        client=object(),  # type: ignore[arg-type]
        base_url="https://example.test",
        reference_year=2025,
    )

    assert package is not None
    assert package_id == "eleitorado-2022"
    assert warnings
    assert "eleitorado-2025" in warnings[0]


def test_extract_rows_from_zip_aggregates_municipality_and_zone_rows() -> None:
    csv_content = (
        "ANO_ELEICAO;NR_ZONA;SG_UF;NM_MUNICIPIO;DS_GENERO;DS_FAIXA_ETARIA;"
        "DS_GRAU_ESCOLARIDADE;QT_ELEITORES_PERFIL\n"
        "2024;145;MG;Diamantina;MASCULINO;25-29;SUPERIOR COMPLETO;10\n"
        "2024;145;MG;Diamantina;MASCULINO;25-29;SUPERIOR COMPLETO;5\n"
        "2024;146;MG;Diamantina;FEMININO;30-34;MEDIO COMPLETO;8\n"
        "2024;146;MG;Outra Cidade;FEMININO;30-34;MEDIO COMPLETO;99\n"
    )
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("perfil_eleitorado_2024.csv", csv_content.encode("latin1"))

    municipality_rows, zone_rows, info = _extract_rows_from_zip(
        zip_bytes=payload.getvalue(),
        municipality_name="Diamantina",
        uf="MG",
        requested_year=2024,
    )
    assert len(municipality_rows) == 2
    assert len(zone_rows) == 2
    assert info["rows_aggregated_municipality"] == 2
    assert info["rows_aggregated_zone"] == 2
    assert info["has_zone_column"] is True


def test_extract_rows_from_zip_works_when_zone_column_is_missing() -> None:
    csv_content = (
        "ANO_ELEICAO;SG_UF;NM_MUNICIPIO;DS_GENERO;DS_FAIXA_ETARIA;DS_GRAU_INSTRUCAO;QT_ELEITORES\n"
        "2024;MG;Diamantina;MASCULINO;25-29;SUPERIOR COMPLETO;10\n"
    )
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("perfil_eleitorado_2024.csv", csv_content.encode("latin1"))

    municipality_rows, zone_rows, info = _extract_rows_from_zip(
        zip_bytes=payload.getvalue(),
        municipality_name="Diamantina",
        uf="MG",
        requested_year=2024,
    )
    assert len(municipality_rows) == 1
    assert zone_rows == []
    assert info["has_zone_column"] is False


def test_extract_rows_from_zip_rewrites_outlier_year_to_requested_year() -> None:
    csv_content = (
        "ANO_ELEICAO;NR_ZONA;SG_UF;NM_MUNICIPIO;DS_GENERO;DS_FAIXA_ETARIA;"
        "DS_GRAU_ESCOLARIDADE;QT_ELEITORES_PERFIL\n"
        "9999;145;MG;Diamantina;MASCULINO;25-29;SUPERIOR COMPLETO;10\n"
    )
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("perfil_eleitorado_9999.csv", csv_content.encode("latin1"))

    municipality_rows, zone_rows, info = _extract_rows_from_zip(
        zip_bytes=payload.getvalue(),
        municipality_name="Diamantina",
        uf="MG",
        requested_year=2024,
    )

    assert len(municipality_rows) == 1
    assert municipality_rows[0]["reference_year"] == 2024
    assert len(zone_rows) == 1
    assert zone_rows[0]["reference_year"] == 2024
    assert info["outlier_year_rows_rewritten"] > 0


def test_extract_section_rows_from_zip_aggregates_and_keeps_section_local_info() -> None:
    csv_content = (
        "ANO_ELEICAO;SG_UF;NM_MUNICIPIO;NR_ZONA;NR_SECAO;NR_LOCAL_VOTACAO;NM_LOCAL_VOTACAO;"
        "DS_GENERO;DS_FAIXA_ETARIA;DS_GRAU_ESCOLARIDADE;QT_ELEITORES_PERFIL\n"
        "2024;MG;Diamantina;145;12;1234;Escola A;MASCULINO;25-29;SUPERIOR COMPLETO;7\n"
        "2024;MG;Diamantina;145;12;1234;Escola A;MASCULINO;25-29;SUPERIOR COMPLETO;3\n"
        "2024;MG;Diamantina;145;13;1235;Escola B;FEMININO;30-34;MEDIO COMPLETO;5\n"
        "2024;MG;Outra Cidade;145;12;1234;Escola A;MASCULINO;25-29;SUPERIOR COMPLETO;99\n"
    )
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("perfil_eleitor_secao_2024_MG.csv", csv_content.encode("latin1"))

    section_rows, info = _extract_section_rows_from_zip(
        zip_bytes=payload.getvalue(),
        municipality_name="Diamantina",
        uf="MG",
        requested_year=2024,
    )

    assert len(section_rows) == 2
    row_12 = next(item for item in section_rows if item["tse_section"] == "12")
    assert row_12["voters"] == 10
    assert row_12["nr_local_votacao"] == "1234"
    assert row_12["local_votacao"] == "Escola A"
    assert info["rows_aggregated_section"] == 2


def test_extract_local_voting_metadata_from_zip_builds_section_index() -> None:
    csv_content = (
        "AA_ELEICAO;SG_UF;NM_MUNICIPIO;NR_ZONA;NR_SECAO;NR_LOCAL_VOTACAO;NM_LOCAL_VOTACAO;QT_ELEITOR_SECAO\n"
        "2024;MG;Diamantina;145;12;1234;Escola A;250\n"
        "2024;MG;Diamantina;145;13;1235;Escola B;180\n"
        "2024;MG;Outra Cidade;145;12;9999;Outro Local;999\n"
    )
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("eleitorado_local_votacao_2024.csv", csv_content.encode("latin1"))

    section_metadata, info = _extract_local_voting_metadata_from_zip(
        zip_bytes=payload.getvalue(),
        municipality_name="Diamantina",
        uf="MG",
        requested_year=2024,
    )

    assert len(section_metadata) == 2
    key = (2024, "145", "12")
    assert key in section_metadata
    assert section_metadata[key]["nr_local_votacao"] == "1234"
    assert section_metadata[key]["local_votacao"] == "Escola A"
    assert section_metadata[key]["voters_section"] == 250
    assert info["rows_aggregated_section"] == 2
