from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PartyIdentity:
    party_number: str
    party_abbr: str | None
    party_name: str | None
    start_year: int = 0
    end_year: int = 9999


_BLANK_OR_NULL_CANDIDATE_NUMBERS = {"95", "96"}
_PROPORTIONAL_OFFICES = {
    "vereador",
    "deputado estadual",
    "deputado distrital",
    "deputado federal",
}

_PARTY_IDENTITIES: tuple[PartyIdentity, ...] = (
    PartyIdentity("10", "PRB", "Partido Republicano Brasileiro", end_year=2018),
    PartyIdentity("10", "REPUBLICANOS", "Republicanos", start_year=2019),
    PartyIdentity("11", "PP", "Partido Progressista", end_year=2018),
    PartyIdentity("11", "PP", "Progressistas", start_year=2019),
    PartyIdentity("12", "PDT", "Partido Democrático Trabalhista"),
    PartyIdentity("13", "PT", "Partido dos Trabalhadores"),
    PartyIdentity("14", "PTB", "Partido Trabalhista Brasileiro"),
    PartyIdentity("15", "MDB", "Movimento Democrático Brasileiro"),
    PartyIdentity("16", "PSTU", "Partido Socialista dos Trabalhadores Unificado"),
    PartyIdentity("17", "PSL", "Partido Social Liberal", end_year=2021),
    PartyIdentity("18", "REDE", "Rede Sustentabilidade"),
    PartyIdentity("19", "PODE", "Podemos", start_year=2017),
    PartyIdentity("19", "PTN", "Partido Trabalhista Nacional", end_year=2016),
    PartyIdentity("20", "PSC", "Partido Social Cristão", end_year=2022),
    PartyIdentity("21", "PCB", "Partido Comunista Brasileiro"),
    PartyIdentity("22", "PR", "Partido da República", end_year=2018),
    PartyIdentity("22", "PL", "Partido Liberal", start_year=2019),
    PartyIdentity("23", "PPS", "Partido Popular Socialista", end_year=2018),
    PartyIdentity("23", "CIDADANIA", "Cidadania", start_year=2019),
    PartyIdentity("25", "DEM", "Democratas", end_year=2023),
    PartyIdentity("25", "PRD", "Partido Renovação Democrática", start_year=2024),
    PartyIdentity("27", "DC", "Democracia Cristã"),
    PartyIdentity("28", "PRTB", "Partido Renovador Trabalhista Brasileiro"),
    PartyIdentity("29", "PCO", "Partido da Causa Operária"),
    PartyIdentity("30", "NOVO", "Partido Novo"),
    PartyIdentity("31", "PHS", "Partido Humanista da Solidariedade", end_year=2019),
    PartyIdentity("33", "PMN", "Partido da Mobilização Nacional"),
    PartyIdentity("35", "PMB", "Partido da Mulher Brasileira"),
    PartyIdentity("36", "PTC", "Partido Trabalhista Cristão", end_year=2022),
    PartyIdentity("40", "PSB", "Partido Socialista Brasileiro"),
    PartyIdentity("43", "PV", "Partido Verde"),
    PartyIdentity("44", "PRP", "Partido Republicano Progressista", end_year=2018),
    PartyIdentity("44", "UNIAO", "União Brasil", start_year=2022),
    PartyIdentity("45", "PSDB", "Partido da Social Democracia Brasileira"),
    PartyIdentity("50", "PSOL", "Partido Socialismo e Liberdade"),
    PartyIdentity("51", "PEN", "Partido Ecológico Nacional", end_year=2017),
    PartyIdentity("51", "PATRIOTA", "Patriota", start_year=2018, end_year=2023),
    PartyIdentity("54", "PPL", "Partido Pátria Livre", end_year=2018),
    PartyIdentity("55", "PSD", "Partido Social Democrático"),
    PartyIdentity("65", "PCdoB", "Partido Comunista do Brasil"),
    PartyIdentity("70", "AVANTE", "AVANTE", start_year=2017),
    PartyIdentity("70", "PTdoB", "Partido Trabalhista do Brasil", end_year=2016),
    PartyIdentity("77", "SOLIDARIEDADE", "Solidariedade"),
    PartyIdentity("80", "UP", "Unidade Popular"),
    PartyIdentity("90", "PROS", "Partido Republicano da Ordem Social", end_year=2024),
)


def _normalize_text(value: str) -> str:
    stripped = value.strip().casefold()
    return "".join(ch for ch in unicodedata.normalize("NFKD", stripped) if not unicodedata.combining(ch))


def _digits_only(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def derive_party_number(candidate_number: Any) -> str | None:
    digits = _digits_only(candidate_number)
    if len(digits) < 2:
        return None
    party_number = digits[:2]
    if party_number in _BLANK_OR_NULL_CANDIDATE_NUMBERS:
        return None
    return party_number


def is_proportional_office(office: Any) -> bool:
    return _normalize_text(str(office or "")) in _PROPORTIONAL_OFFICES


def is_party_legend_row(*, office: Any, candidate_number: Any, candidate_name: Any) -> bool:
    party_number = derive_party_number(candidate_number)
    if party_number is None or _digits_only(candidate_number) != party_number:
        return False
    if not is_proportional_office(office):
        return False
    normalized_name = _normalize_text(str(candidate_name or ""))
    return normalized_name not in {"", "voto branco", "voto nulo"}


def lookup_party_identity(
    *,
    party_number: str | None,
    election_year: int | None,
    party_name: str | None = None,
) -> PartyIdentity | None:
    if party_number is None:
        return None

    normalized_name = _normalize_text(party_name or "")
    exact_name_match: PartyIdentity | None = None
    exact_number_match: PartyIdentity | None = None

    for identity in _PARTY_IDENTITIES:
        if identity.party_number != party_number:
            continue
        if election_year is not None and not (identity.start_year <= election_year <= identity.end_year):
            continue
        if normalized_name and identity.party_name and _normalize_text(identity.party_name) == normalized_name:
            exact_name_match = identity
            break
        if exact_number_match is None:
            exact_number_match = identity

    if exact_name_match is not None:
        return exact_name_match
    if exact_number_match is not None:
        return exact_number_match

    if normalized_name:
        for identity in _PARTY_IDENTITIES:
            if identity.party_name and _normalize_text(identity.party_name) == normalized_name:
                if election_year is None or (identity.start_year <= election_year <= identity.end_year):
                    return identity
    return None


def build_party_lookup(rows: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, str | None]]:
    lookup: dict[tuple[int, str], dict[str, str | None]] = {}

    for row in rows:
        election_year = int(row["election_year"])
        candidate_number = row.get("candidate_number")
        candidate_name = row.get("candidate_name")
        if not is_party_legend_row(
            office=row.get("office"),
            candidate_number=candidate_number,
            candidate_name=candidate_name,
        ):
            continue
        party_number = derive_party_number(candidate_number)
        if party_number is None:
            continue

        explicit_party_name = row.get("party_name") or str(candidate_name or "").strip() or None
        identity = lookup_party_identity(
            party_number=party_number,
            election_year=election_year,
            party_name=explicit_party_name,
        )
        party_name = explicit_party_name
        if identity is not None and identity.party_name:
            party_name = identity.party_name

        lookup[(election_year, party_number)] = {
            "party_number": party_number,
            "party_abbr": identity.party_abbr if identity is not None else None,
            "party_name": party_name,
        }

    return lookup


def enrich_candidate_row_party(
    row: dict[str, Any],
    *,
    party_lookup: dict[tuple[int, str], dict[str, str | None]] | None = None,
) -> dict[str, Any]:
    party_number = row.get("party_number") or derive_party_number(row.get("candidate_number"))
    if party_number is None:
        return row

    election_year = int(row["election_year"])
    lookup_entry = (party_lookup or {}).get((election_year, party_number))
    identity = lookup_party_identity(
        party_number=party_number,
        election_year=election_year,
        party_name=(lookup_entry or {}).get("party_name") or row.get("party_name"),
    )

    if row.get("party_number") is None:
        row["party_number"] = party_number
    if row.get("party_abbr") is None and lookup_entry and lookup_entry.get("party_abbr"):
        row["party_abbr"] = lookup_entry["party_abbr"]
    if row.get("party_name") is None and lookup_entry and lookup_entry.get("party_name"):
        row["party_name"] = lookup_entry["party_name"]

    if row.get("party_abbr") is None and identity is not None and identity.party_abbr:
        row["party_abbr"] = identity.party_abbr
    if row.get("party_name") is None and identity is not None and identity.party_name:
        row["party_name"] = identity.party_name

    return row


def enrich_candidate_rows_with_party(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    party_lookup = build_party_lookup(rows)
    for row in rows:
        enrich_candidate_row_party(row, party_lookup=party_lookup)
    return rows
