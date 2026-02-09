from __future__ import annotations

from pipelines.tse_results import _normalize_text, _pick_results_resource


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
