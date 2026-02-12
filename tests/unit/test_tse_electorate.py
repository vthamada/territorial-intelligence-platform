from __future__ import annotations

import pytest

from pipelines.tse_electorate import (
    _normalize_text,
    _pick_electorate_resource,
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


def test_resolve_electorate_columns_raises_when_required_missing() -> None:
    columns = ["ANO_ELEICAO", "SG_UF"]
    with pytest.raises(ValueError):
        _resolve_electorate_columns(columns)
