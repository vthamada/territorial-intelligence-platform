from __future__ import annotations

import io
import zipfile

from pipelines.tse_candidate_votes import (
    _derive_election_type,
    _extract_rows_from_zip,
    _pick_candidate_votes_resource,
)


def _zip_with_csv(csv_name: str, csv_content: str) -> bytes:
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(csv_name, csv_content.encode("latin1"))
    return raw.getvalue()


def test_pick_candidate_votes_resource_prefers_nominal_munzona_zip() -> None:
    resources = [
        {
            "name": "BR - Votacao por secao eleitoral - 2022",
            "url": "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2022_BR.zip",
        },
        {
            "name": "MG - Votacao por secao eleitoral - 2022",
            "url": "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2022_MG.zip",
        },
    ]
    selected = _pick_candidate_votes_resource(resources, uf="MG")
    assert selected is not None
    assert selected["url"].endswith("_MG.zip")


def test_extract_rows_from_zip_parses_candidate_votes_with_section_and_polling_place() -> None:
    csv_content = (
        "ANO_ELEICAO;NR_TURNO;SG_UF;NM_MUNICIPIO;DS_CARGO;NR_ZONA;NR_SECAO;NR_LOCAL_VOTACAO;NM_LOCAL_VOTACAO;DS_LOCAL_VOTACAO_ENDERECO;"
        "NM_URNA_CANDIDATO;NR_VOTAVEL;SG_PARTIDO;NR_PARTIDO;NM_PARTIDO;QT_VOTOS_NOMINAIS\n"
        "2024;1;MG;Diamantina;Prefeito;0101;0041;101;UEMG (ANTIGA FEVALE);Rua da Gloria, 12;Candidato A;13;PT;13;Partido dos Testes;123\n"
    )
    zip_bytes = _zip_with_csv("votacao_mg.csv", csv_content)

    rows, parse_info = _extract_rows_from_zip(
        zip_bytes=zip_bytes,
        municipality_name="Diamantina",
        uf="MG",
    )

    assert rows == [
        {
            "election_year": 2024,
            "election_round": 1,
            "office": "Prefeito",
            "election_type": "municipal",
            "tse_zone": "101",
            "tse_section": "41",
            "polling_place_name": "UEMG (ANTIGA FEVALE)",
            "polling_place_code": "101",
            "polling_place_address": "Rua da Gloria, 12",
            "candidate_number": "13",
            "candidate_name": "Candidato A",
            "ballot_name": "Candidato A",
            "full_name": None,
            "party_abbr": "PT",
            "party_number": "13",
            "party_name": "Partido dos Testes",
            "votes": 123,
        }
    ]
    assert parse_info["candidates_detected"] == 1
    assert parse_info["sections_detected"] == 1


def test_derive_election_type_uses_office_semantics() -> None:
    assert _derive_election_type("Prefeito") == "municipal"
    assert _derive_election_type("Presidente") == "general"
    assert _derive_election_type("Conselheiro") == "other"
