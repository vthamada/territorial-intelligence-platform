from __future__ import annotations

import io
import zipfile

import pytest

from pipelines.tse_electorate import (
    _extract_rows_from_zip,
    _normalize_text,
    _pick_electorate_resource,
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
