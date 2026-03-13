from __future__ import annotations

import io
import zipfile

from pipelines.tse_candidate_votes import (
    _build_direct_candidate_vote_resources,
    _derive_election_type,
    _extract_rows_from_zip,
    _merge_candidate_vote_rows,
    _pick_candidate_votes_resources,
    _pick_candidate_votes_resource,
)
from pipelines.tse_party_registry import (
    build_party_lookup,
    enrich_candidate_row_party,
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


def test_pick_candidate_votes_resources_adds_president_supplement_for_general_year() -> None:
    resources = [
        {
            "name": "MG - Votacao por secao eleitoral - 2022",
            "url": "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2022_MG.zip",
        },
        {
            "name": "Presidente - Votacao por secao eleitoral - 2022",
            "url": "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2022_BR.zip",
        },
    ]

    selected = _pick_candidate_votes_resources(resources, uf="MG", reference_year=2022)

    assert len(selected) == 2
    assert selected[0]["dataset"] == "tse_votacao_secao"
    assert selected[0]["allowed_offices"] is None
    assert str(selected[0]["resource"]["url"]).endswith("_MG.zip")
    assert selected[1]["dataset"] == "tse_votacao_secao_presidente"
    assert selected[1]["allowed_offices"] == {"presidente"}
    assert str(selected[1]["resource"]["url"]).endswith("_BR.zip")


def test_build_direct_candidate_vote_resources_adds_br_supplement_for_2022() -> None:
    selected = _build_direct_candidate_vote_resources(uf="MG", reference_year=2022)

    assert len(selected) == 2
    assert str(selected[0]["resource"]["url"]).endswith("votacao_secao_2022_MG.zip")
    assert str(selected[1]["resource"]["url"]).endswith("votacao_secao_2022_BR.zip")
    assert selected[1]["allowed_offices"] == {"presidente"}


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


def test_extract_rows_from_zip_filters_allowed_offices() -> None:
    csv_content = (
        "ANO_ELEICAO;NR_TURNO;SG_UF;NM_MUNICIPIO;DS_CARGO;NR_ZONA;NR_SECAO;NR_LOCAL_VOTACAO;NM_LOCAL_VOTACAO;DS_LOCAL_VOTACAO_ENDERECO;"
        "NM_URNA_CANDIDATO;NR_VOTAVEL;SG_PARTIDO;NR_PARTIDO;NM_PARTIDO;QT_VOTOS_NOMINAIS\n"
        "2022;1;MG;Diamantina;Governador;0101;0041;101;UEMG;Rua da Gloria, 12;Candidato A;13;PT;13;Partido dos Testes;123\n"
        "2022;1;MG;Diamantina;Presidente;0101;0041;101;UEMG;Rua da Gloria, 12;Candidato B;22;PL;22;Partido B;321\n"
    )
    zip_bytes = _zip_with_csv("votacao_mg.csv", csv_content)

    rows, parse_info = _extract_rows_from_zip(
        zip_bytes=zip_bytes,
        municipality_name="Diamantina",
        uf="MG",
        allowed_offices={"presidente"},
    )

    assert len(rows) == 1
    assert rows[0]["office"] == "Presidente"
    assert rows[0]["votes"] == 321
    assert parse_info["rows_aggregated"] == 1


def test_merge_candidate_vote_rows_avoids_double_counting_duplicates() -> None:
    base_row = {
        "election_year": 2022,
        "election_round": 1,
        "office": "Presidente",
        "election_type": "general",
        "tse_zone": "101",
        "tse_section": "41",
        "polling_place_name": "UEMG",
        "polling_place_code": "101",
        "polling_place_address": "Rua da Gloria, 12",
        "candidate_number": "13",
        "candidate_name": "Candidato A",
        "ballot_name": "Candidato A",
        "full_name": None,
        "party_abbr": "PT",
        "party_number": "13",
        "party_name": "Partido A",
        "votes": 123,
    }
    combined: dict[tuple[object, ...], dict[str, object]] = {}
    warnings: list[str] = []

    _merge_candidate_vote_rows(combined, [base_row], source_label="mg", warnings=warnings)
    _merge_candidate_vote_rows(combined, [dict(base_row)], source_label="br", warnings=warnings)

    assert len(combined) == 1
    assert warnings == []


def test_party_lookup_infers_prefeito_party_from_vereador_legend_rows() -> None:
    rows = [
        {
            "election_year": 2024,
            "office": "Vereador",
            "candidate_number": "15",
            "candidate_name": "Movimento Democrático Brasileiro",
            "party_abbr": None,
            "party_number": None,
            "party_name": None,
        },
        {
            "election_year": 2024,
            "office": "Prefeito",
            "candidate_number": "15",
            "candidate_name": "Candidato A",
            "party_abbr": None,
            "party_number": None,
            "party_name": None,
        },
    ]

    lookup = build_party_lookup(rows)
    enriched = enrich_candidate_row_party(dict(rows[1]), party_lookup=lookup)

    assert enriched["party_number"] == "15"
    assert enriched["party_abbr"] == "MDB"
    assert enriched["party_name"] == "Movimento Democrático Brasileiro"


def test_party_lookup_uses_historical_registry_when_legend_row_missing() -> None:
    row = {
        "election_year": 2022,
        "office": "PRESIDENTE",
        "candidate_number": "22",
        "candidate_name": "JAIR MESSIAS BOLSONARO",
        "party_abbr": None,
        "party_number": None,
        "party_name": None,
    }

    enriched = enrich_candidate_row_party(dict(row), party_lookup={})

    assert enriched["party_number"] == "22"
    assert enriched["party_abbr"] == "PL"
    assert enriched["party_name"] == "Partido Liberal"


def test_derive_election_type_uses_office_semantics() -> None:
    assert _derive_election_type("Prefeito") == "municipal"
    assert _derive_election_type("Presidente") == "general"
    assert _derive_election_type("Conselheiro") == "other"
