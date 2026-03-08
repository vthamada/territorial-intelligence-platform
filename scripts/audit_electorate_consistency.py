from __future__ import annotations

import argparse
import csv
import json
import math
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.api.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "reports" / "electorate_consistency_audit.json"
PROFILE_ROOT = PROJECT_ROOT / "data" / "bronze" / "tse" / "tse_perfil_eleitorado"
RESULT_ROOT = PROJECT_ROOT / "data" / "bronze" / "tse" / "tse_detalhe_votacao_munzona"
CANDIDATE_ROOT = PROJECT_ROOT / "data" / "bronze" / "tse" / "tse_votacao_secao"
YEARS = [2016, 2018, 2020, 2022, 2024]


@dataclass
class ParticipationScope:
    office: str
    election_round: int | None
    election_type: str | None
    electorate_total: int
    turnout: int
    abstention: int
    votes_blank: int
    votes_null: int

    def rates(self) -> dict[str, float | None]:
        turnout_rate = (self.turnout / self.electorate_total) * 100 if self.electorate_total else None
        abstention_rate = (self.abstention / self.electorate_total) * 100 if self.electorate_total else None
        blank_rate = (self.votes_blank / self.turnout) * 100 if self.turnout else None
        null_rate = (self.votes_null / self.turnout) * 100 if self.turnout else None
        return {
            "turnout_rate": turnout_rate,
            "abstention_rate": abstention_rate,
            "blank_rate": blank_rate,
            "null_rate": null_rate,
        }


def approx_equal(left: float | int | None, right: float | int | None, tolerance: float = 1e-6) -> bool:
    if left is None or right is None:
        return left is right
    return math.isclose(float(left), float(right), rel_tol=0, abs_tol=tolerance)


def latest_extracted_zip(root: Path, year: int) -> Path:
    year_root = root / str(year)
    candidates = sorted(year_root.glob("extracted_at=*/raw.zip"))
    if not candidates:
        raise FileNotFoundError(f"raw ZIP not found under {year_root}")
    return candidates[-1]


def iter_csv_rows_from_zip(path: Path, *, member_predicate: callable | None = None) -> Iterable[dict[str, str]]:
    with zipfile.ZipFile(path) as zf:
        names = [name for name in zf.namelist() if name.lower().endswith(".csv")]
        if member_predicate is not None:
            names = [name for name in names if member_predicate(name)]
        for name in names:
            with zf.open(name) as handle:
                reader = csv.DictReader(
                    (line.decode("latin-1", errors="replace") for line in handle),
                    delimiter=";",
                )
                yield from reader


def load_raw_profile(municipality_name: str, municipality_uf: str, year: int) -> dict[str, Any]:
    path = latest_extracted_zip(PROFILE_ROOT, year)

    total_voters = 0
    by_sex: dict[str, int] = defaultdict(int)
    by_age: dict[str, int] = defaultdict(int)
    by_education: dict[str, int] = defaultdict(int)

    for row in iter_csv_rows_from_zip(path):
        if row["NM_MUNICIPIO"].strip().upper() != municipality_name.upper() or row["SG_UF"].strip().upper() != municipality_uf.upper():
            continue
        voters = int(row["QT_ELEITORES_PERFIL"])
        total_voters += voters
        by_sex[row["DS_GENERO"]] += voters
        by_age[row["DS_FAIXA_ETARIA"]] += voters
        by_education[row["DS_GRAU_ESCOLARIDADE"]] += voters

    return {
        "zip_path": str(path.relative_to(PROJECT_ROOT)),
        "total_voters": total_voters,
        "by_sex": dict(sorted(by_sex.items(), key=lambda item: (-item[1], item[0]))),
        "by_age": dict(sorted(by_age.items(), key=lambda item: (-item[1], item[0]))),
        "by_education": dict(sorted(by_education.items(), key=lambda item: (-item[1], item[0]))),
    }


def load_raw_result_scopes(municipality_name: str, municipality_uf: str, year: int) -> list[ParticipationScope]:
    path = latest_extracted_zip(RESULT_ROOT, year)
    grouped: dict[tuple[str, int | None, str | None], dict[str, int | str | None]] = {}

    for row in iter_csv_rows_from_zip(path, member_predicate=lambda name: name.lower().endswith("_mg.csv")):
        if row["NM_MUNICIPIO"].strip().upper() != municipality_name.upper() or row["SG_UF"].strip().upper() != municipality_uf.upper():
            continue
        office = row["DS_CARGO"].strip()
        election_round = int(row["NR_TURNO"]) if row["NR_TURNO"] else None
        election_type = row["NM_TIPO_ELEICAO"].strip() if row["NM_TIPO_ELEICAO"] else None
        key = (office, election_round, election_type)
        grouped.setdefault(
            key,
            {
                "office": office,
                "election_round": election_round,
                "election_type": election_type,
                "electorate_total": 0,
                "turnout": 0,
                "abstention": 0,
                "votes_blank": 0,
                "votes_null": 0,
            },
        )
        grouped[key]["electorate_total"] += int(row["QT_APTOS"] or 0)
        grouped[key]["turnout"] += int(row["QT_COMPARECIMENTO"] or 0)
        grouped[key]["abstention"] += int(row["QT_ABSTENCOES"] or 0)
        grouped[key]["votes_blank"] += int(row["QT_VOTOS_BRANCOS"] or 0)
        grouped[key]["votes_null"] += int(row["QT_TOTAL_VOTOS_NULOS"] or 0)

    scopes = [
        ParticipationScope(
            office=str(values["office"]),
            election_round=values["election_round"],  # type: ignore[arg-type]
            election_type=values["election_type"],  # type: ignore[arg-type]
            electorate_total=int(values["electorate_total"]),
            turnout=int(values["turnout"]),
            abstention=int(values["abstention"]),
            votes_blank=int(values["votes_blank"]),
            votes_null=int(values["votes_null"]),
        )
        for values in grouped.values()
    ]
    return sorted(scopes, key=lambda item: (-item.turnout, item.office, item.election_round or 0))


def load_raw_candidate_scopes(municipality_name: str, municipality_uf: str, year: int) -> dict[str, Any]:
    year_root = CANDIDATE_ROOT / str(year)
    if not year_root.exists():
        return {
            "zip_path": None,
            "available": False,
            "note": f"candidate_bronze_missing_for_year_{year}",
            "items": [],
        }

    path = latest_extracted_zip(CANDIDATE_ROOT, year)
    grouped: dict[tuple[str, int | None], dict[str, Any]] = {}

    for row in iter_csv_rows_from_zip(path, member_predicate=lambda name: name.lower().endswith("_mg.csv")):
        if row["NM_MUNICIPIO"].strip().upper() != municipality_name.upper() or row["SG_UF"].strip().upper() != municipality_uf.upper():
            continue
        office = row.get("DS_CARGO", "").strip() or "NÃO INFORMADO"
        election_round = int(row["NR_TURNO"]) if row.get("NR_TURNO") else None
        votes = int(row.get("QT_VOTOS_NOMINAIS") or row.get("QT_VOTOS") or 0)
        candidate_number = str(row.get("NR_VOTAVEL") or row.get("NR_CANDIDATO") or "").strip()
        candidate_name = str(row.get("NM_VOTAVEL") or row.get("NM_URNA_CANDIDATO") or row.get("NM_CANDIDATO") or "").strip()
        section_code = str(row.get("NR_SECAO") or "").strip()
        polling_place_name = str(row.get("NM_LOCAL_VOTACAO") or "").strip()
        polling_place_code = str(row.get("NR_LOCAL_VOTACAO") or row.get("CD_LOCAL_VOTACAO") or "").strip()
        key = (office, election_round)
        scope = grouped.setdefault(
            key,
            {
                "office": office,
                "election_round": election_round,
                "candidate_votes": defaultdict(int),
                "section_codes": set(),
                "polling_place_keys": set(),
            },
        )
        if candidate_number or candidate_name:
            scope["candidate_votes"][(candidate_number, candidate_name)] += votes
        if section_code:
            scope["section_codes"].add(section_code)
        if polling_place_name or polling_place_code:
            scope["polling_place_keys"].add((polling_place_code, polling_place_name))

    items: list[dict[str, Any]] = []
    for (_, _), scope in grouped.items():
        top_candidates = sorted(
            (
                {
                    "candidate_number": number,
                    "candidate_name": name,
                    "votes": total_votes,
                }
                for (number, name), total_votes in scope["candidate_votes"].items()
            ),
            key=lambda item: (-item["votes"], item["candidate_name"], item["candidate_number"]),
        )[:5]
        items.append(
            {
                "office": scope["office"],
                "election_round": scope["election_round"],
                "candidate_count": len(scope["candidate_votes"]),
                "section_count": len(scope["section_codes"]),
                "polling_place_count": len(scope["polling_place_keys"]),
                "top_candidates": top_candidates,
            }
        )

    items.sort(key=lambda item: (item["office"], item["election_round"] or 0))
    return {
        "zip_path": str(path.relative_to(PROJECT_ROOT)),
        "available": True,
        "items": items,
    }


def build_db_engine() -> Any:
    cfg = dotenv_values(PROJECT_ROOT / ".env")
    database_url = cfg.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not configured in .env")
    return create_engine(database_url)


def municipality_context(conn: Any, municipality_code: str) -> tuple[str, str, str]:
    row = conn.execute(
        text(
            """
            SELECT territory_id::text AS territory_id, name, uf
            FROM silver.dim_territory
            WHERE level = 'municipality'
              AND municipality_ibge_code = :municipality_code
            LIMIT 1
            """
        ),
        {"municipality_code": municipality_code},
    ).mappings().one()
    return str(row["territory_id"]), str(row["name"]), str(row["uf"])


def db_electorate_total(conn: Any, territory_id: str, year: int) -> int:
    value = conn.execute(
        text(
            """
            SELECT COALESCE(SUM(voters), 0)
            FROM silver.fact_electorate
            WHERE territory_id::text = :territory_id
              AND reference_year = :year
            """
        ),
        {"territory_id": territory_id, "year": year},
    ).scalar_one()
    return int(value or 0)


def db_breakdown(conn: Any, territory_id: str, year: int, column_name: str) -> dict[str, int]:
    rows = conn.execute(
        text(
            f"""
            SELECT {column_name} AS label, SUM(voters)::bigint AS voters
            FROM silver.fact_electorate
            WHERE territory_id::text = :territory_id
              AND reference_year = :year
            GROUP BY {column_name}
            ORDER BY SUM(voters) DESC, {column_name} ASC
            """
        ),
        {"territory_id": territory_id, "year": year},
    ).mappings().all()
    return {str(row["label"]): int(row["voters"]) for row in rows}


def db_result_scopes(conn: Any, territory_id: str, year: int) -> list[ParticipationScope]:
    rows = conn.execute(
        text(
            """
            SELECT
                office,
                election_round,
                MAX(CASE WHEN metric = 'turnout' THEN value END)::bigint AS turnout,
                MAX(CASE WHEN metric = 'abstention' THEN value END)::bigint AS abstention,
                MAX(CASE WHEN metric = 'votes_blank' THEN value END)::bigint AS votes_blank,
                MAX(CASE WHEN metric = 'votes_null' THEN value END)::bigint AS votes_null
            FROM silver.fact_election_result
            WHERE territory_id::text = :territory_id
              AND election_year = :year
            GROUP BY office, election_round
            """
        ),
        {"territory_id": territory_id, "year": year},
    ).mappings().all()

    electorate_total = db_electorate_total(conn, territory_id, year)
    scopes = [
        ParticipationScope(
            office=row["office"],
            election_round=int(row["election_round"]) if row["election_round"] is not None else None,
            election_type=None,
            electorate_total=electorate_total,
            turnout=int(row["turnout"] or 0),
            abstention=int(row["abstention"] or 0),
            votes_blank=int(row["votes_blank"] or 0),
            votes_null=int(row["votes_null"] or 0),
        )
        for row in rows
    ]
    return sorted(scopes, key=lambda item: (-item.turnout, item.office, item.election_round or 0))


def match_scope_to_api(api_item: dict[str, Any], scopes: list[ParticipationScope]) -> ParticipationScope | None:
    if not scopes:
        return None

    def score(scope: ParticipationScope) -> tuple[float, float, float, float]:
        rates = scope.rates()
        return (
            abs(float(api_item["turnout"] or 0) - scope.turnout),
            abs(float(api_item["turnout_rate"] or 0) - float(rates["turnout_rate"] or 0)),
            abs(float(api_item["blank_rate"] or 0) - float(rates["blank_rate"] or 0)),
            abs(float(api_item["null_rate"] or 0) - float(rates["null_rate"] or 0)),
        )

    return min(scopes, key=score)


def db_polling_places_top(conn: Any, year: int, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            WITH grouped AS (
                SELECT
                    COALESCE(NULLIF(dt.metadata->>'polling_place_name', ''), dt.name) AS polling_place_name,
                    NULLIF(dt.metadata->>'polling_place_code', '') AS polling_place_code,
                    COALESCE(NULLIF(dt.metadata->>'district_name', ''), district.name) AS district_name,
                    ARRAY_REMOVE(ARRAY_AGG(DISTINCT NULLIF(dt.tse_zone, '')), NULL) AS zone_codes,
                    ARRAY_AGG(DISTINCT dt.tse_section ORDER BY dt.tse_section) FILTER (WHERE NULLIF(dt.tse_section, '') IS NOT NULL) AS sections,
                    COUNT(DISTINCT dt.territory_id)::int AS section_count,
                    SUM(fe.voters)::bigint AS voters_total
                FROM silver.fact_electorate fe
                JOIN silver.dim_territory dt ON dt.territory_id = fe.territory_id
                LEFT JOIN LATERAL (
                    SELECT d.name
                    FROM silver.dim_territory d
                    WHERE d.level = 'district'
                      AND d.geometry IS NOT NULL
                      AND dt.geometry IS NOT NULL
                      AND ST_Covers(d.geometry, dt.geometry)
                    ORDER BY d.name
                    LIMIT 1
                ) district ON TRUE
                WHERE dt.level = 'electoral_section'
                  AND dt.municipality_ibge_code = '3121605'
                  AND fe.reference_year = :year
                GROUP BY 1, 2, 3
            ),
            total AS (
                SELECT SUM(voters_total)::double precision AS municipality_total
                FROM grouped
            )
            SELECT
                polling_place_name,
                polling_place_code,
                district_name,
                zone_codes,
                sections,
                section_count,
                voters_total,
                CASE
                    WHEN total.municipality_total > 0 THEN (grouped.voters_total / total.municipality_total) * 100
                    ELSE NULL
                END AS share_percent
            FROM grouped
            CROSS JOIN total
            ORDER BY voters_total DESC, polling_place_name ASC
            LIMIT :limit
            """
        ),
        {"year": year, "limit": limit},
    ).mappings().all()
    return [dict(row) for row in rows]


def candidate_tables_available(conn: Any) -> bool:
    row = conn.execute(
        text(
            """
            SELECT
                to_regclass('silver.fact_candidate_vote') IS NOT NULL AS fact_candidate_vote,
                to_regclass('silver.dim_candidate') IS NOT NULL AS dim_candidate,
                to_regclass('silver.dim_election') IS NOT NULL AS dim_election
            """
        )
    ).mappings().one()
    return all(bool(value) for value in row.values())


def db_candidate_scope_rows(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT
                de.election_year,
                dt.level::text AS territory_level,
                de.office,
                de.election_round,
                COUNT(*)::bigint AS fact_rows,
                (COUNT(DISTINCT dt.tse_section) FILTER (WHERE dt.level::text = 'electoral_section'))::bigint AS section_count,
                (
                    COUNT(DISTINCT COALESCE(NULLIF(dt.metadata->>'polling_place_code', ''), NULLIF(dt.metadata->>'polling_place_name', ''), dt.name))
                    FILTER (WHERE dt.level::text = 'electoral_section')
                )::bigint AS polling_place_count,
                SUM(fcv.votes)::bigint AS votes_total
            FROM silver.fact_candidate_vote fcv
            JOIN silver.dim_election de ON de.election_id = fcv.election_id
            JOIN silver.dim_territory dt ON dt.territory_id = fcv.territory_id
            GROUP BY de.election_year, dt.level::text, de.office, de.election_round
            ORDER BY de.election_year DESC, dt.level::text ASC, de.office ASC, de.election_round ASC NULLS LAST
            """
        )
    ).mappings().all()
    return [dict(row) for row in rows]


def db_top_candidates_for_scope(conn: Any, *, year: int, office: str, election_round: int | None) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT
                dc.candidate_number,
                dc.candidate_name,
                SUM(fcv.votes)::bigint AS votes
            FROM silver.fact_candidate_vote fcv
            JOIN silver.dim_candidate dc ON dc.candidate_id = fcv.candidate_id
            JOIN silver.dim_election de ON de.election_id = fcv.election_id
            JOIN silver.dim_territory dt ON dt.territory_id = fcv.territory_id
            WHERE de.election_year = :year
              AND de.office = :office
              AND de.election_round IS NOT DISTINCT FROM :election_round
              AND dt.level::text = 'electoral_section'
            GROUP BY dc.candidate_number, dc.candidate_name
            ORDER BY votes DESC, dc.candidate_name ASC, dc.candidate_number ASC
            LIMIT 5
            """
        ),
        {"year": year, "office": office, "election_round": election_round},
    ).mappings().all()
    return [dict(row) for row in rows]


def composition_report(api_summary: dict[str, Any], raw_profile: dict[str, Any], conn: Any, territory_id: str) -> dict[str, Any]:
    year = int(api_summary["year"])
    db_sex = db_breakdown(conn, territory_id, year, "sex")
    db_age = db_breakdown(conn, territory_id, year, "age_range")
    db_education = db_breakdown(conn, territory_id, year, "education")

    def compare(api_items: list[dict[str, Any]], db_items: dict[str, int], raw_items: dict[str, int]) -> dict[str, Any]:
        mismatches: list[dict[str, Any]] = []
        for item in api_items:
            label = item["label"]
            api_voters = int(item["voters"])
            db_voters = int(db_items.get(label, 0))
            raw_voters = int(raw_items.get(label, 0))
            if not (api_voters == db_voters == raw_voters):
                mismatches.append(
                    {
                        "label": label,
                        "api_voters": api_voters,
                        "db_voters": db_voters,
                        "raw_voters": raw_voters,
                    }
                )
        return {
            "api_labels": len(api_items),
            "db_labels": len(db_items),
            "raw_labels": len(raw_items),
            "mismatches": mismatches,
        }

    return {
        "sex": compare(api_summary["by_sex"], db_sex, raw_profile["by_sex"]),
        "age": compare(api_summary["by_age"], db_age, raw_profile["by_age"]),
        "education": compare(api_summary["by_education"], db_education, raw_profile["by_education"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--municipality-code", default="3121605")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--years", default="2016,2018,2020,2022,2024")
    args = parser.parse_args()
    audit_years = [
        int(token.strip())
        for token in str(args.years).split(",")
        if token.strip()
    ]

    client = TestClient(app)
    engine = build_db_engine()

    summary_response = client.get("/v1/electorate/summary", params={"level": "municipality", "year": 2024}).json()
    history_response = client.get("/v1/electorate/history", params={"level": "municipality", "limit": len(YEARS)}).json()
    polling_response = client.get("/v1/electorate/polling-places", params={"year": 2024, "metric": "voters", "limit": 5}).json()
    election_context_response = client.get(
        "/v1/electorate/election-context",
        params={"level": "municipality", "year": 2024, "limit": 5},
    ).json()

    with engine.connect() as conn:
        territory_id, municipality_name, municipality_uf = municipality_context(conn, args.municipality_code)
        raw_profiles = {year: load_raw_profile(municipality_name, municipality_uf, year) for year in audit_years}
        raw_scopes = {year: load_raw_result_scopes(municipality_name, municipality_uf, year) for year in audit_years}
        raw_candidate_scopes = {year: load_raw_candidate_scopes(municipality_name, municipality_uf, year) for year in audit_years}
        db_totals = {year: db_electorate_total(conn, territory_id, year) for year in audit_years}
        db_scopes = {year: db_result_scopes(conn, territory_id, year) for year in audit_years}
        composition_checks = composition_report(summary_response, raw_profiles[2024], conn, territory_id)
        polling_db = db_polling_places_top(conn, 2024, 5)
        candidate_tables = candidate_tables_available(conn)
        db_candidate_scopes = db_candidate_scope_rows(conn) if candidate_tables else []
        db_top_candidates_api_scope = (
            []
            if not candidate_tables
            or not election_context_response["items"]
            or election_context_response["year"] is None
            or election_context_response.get("office") is None
            else db_top_candidates_for_scope(
                conn,
                year=int(election_context_response["year"]),
                office=str(election_context_response["office"]),
                election_round=election_context_response.get("election_round"),
            )
        )

    history_checks: list[dict[str, Any]] = []
    for item in history_response["items"]:
        year = int(item["year"])
        if year not in raw_profiles:
            continue
        raw_scope = match_scope_to_api(item, raw_scopes.get(year, []))
        db_scope = match_scope_to_api(item, db_scopes.get(year, []))
        raw_rates = raw_scope.rates() if raw_scope else {}
        db_rates = db_scope.rates() if db_scope else {}
        history_checks.append(
            {
                "year": year,
                "api_total_voters": item["total_voters"],
                "db_total_voters": db_totals[year],
                "raw_total_voters": raw_profiles[year]["total_voters"],
                "totals_match": item["total_voters"] == raw_profiles[year]["total_voters"],
                "matched_db_scope": None
                if db_scope is None
                else {
                    "office": db_scope.office,
                    "election_round": db_scope.election_round,
                    "turnout": db_scope.turnout,
                    "abstention": db_scope.abstention,
                    "votes_blank": db_scope.votes_blank,
                    "votes_null": db_scope.votes_null,
                    **db_rates,
                },
                "matched_raw_scope": None
                if raw_scope is None
                else {
                    "office": raw_scope.office,
                    "election_round": raw_scope.election_round,
                    "election_type": raw_scope.election_type,
                    "turnout": raw_scope.turnout,
                    "abstention": raw_scope.abstention,
                    "votes_blank": raw_scope.votes_blank,
                    "votes_null": raw_scope.votes_null,
                    **raw_rates,
                },
                "api_metrics": {
                    "turnout": item["turnout"],
                    "turnout_rate": item["turnout_rate"],
                    "abstention_rate": item["abstention_rate"],
                    "blank_rate": item["blank_rate"],
                    "null_rate": item["null_rate"],
                },
                "metrics_match_raw": raw_scope is not None
                and approx_equal(item["turnout"], raw_scope.turnout)
                and approx_equal(item["turnout_rate"], raw_rates["turnout_rate"])
                and approx_equal(item["abstention_rate"], raw_rates["abstention_rate"])
                and approx_equal(item["blank_rate"], raw_rates["blank_rate"])
                and approx_equal(item["null_rate"], raw_rates["null_rate"]),
            }
        )

    polling_checks = []
    for api_item, db_item in zip(polling_response["items"], polling_db, strict=False):
        polling_checks.append(
            {
                "polling_place_name": api_item["polling_place_name"],
                "api_voters_total": api_item["voters_total"],
                "db_voters_total": int(db_item["voters_total"]),
                "api_section_count": api_item["section_count"],
                "db_section_count": int(db_item["section_count"]),
                "api_share_percent": api_item["share_percent"],
                "db_share_percent": float(db_item["share_percent"]) if db_item["share_percent"] is not None else None,
                "matches_db": api_item["polling_place_name"] == db_item["polling_place_name"]
                and int(api_item["voters_total"]) == int(db_item["voters_total"])
                and int(api_item["section_count"]) == int(db_item["section_count"]),
            }
        )

    report = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "municipality_ibge_code": args.municipality_code,
        "municipality_name": municipality_name,
        "municipality_uf": municipality_uf,
        "api_summary_2024": {
            key: summary_response[key]
            for key in [
                "level",
                "year",
                "total_voters",
                "turnout",
                "turnout_rate",
                "abstention_rate",
                "blank_rate",
                "null_rate",
            ]
        },
        "history_checks": history_checks,
        "composition_checks_2024": composition_checks,
        "polling_place_checks_2024": {
            "raw_source_supports_polling_place": False,
            "note": "O bruto do perfil do eleitorado não expõe local de votação; a auditoria do ranking é feita contra a agregação Silver por seção/local.",
            "items": polling_checks,
        },
        "candidate_context": {
            "tables_available": candidate_tables,
            "api_year": election_context_response["year"],
            "api_notes": election_context_response["metadata"]["notes"],
            "items_count": len(election_context_response["items"]),
        },
        "candidate_nominal_checks": {
            "raw_source": {
                str(year): raw_candidate_scopes[year]
                for year in audit_years
            },
            "db_scope_rows": db_candidate_scopes,
            "year_summary": [
                {
                    "year": year,
                    "raw_offices": [
                        {
                            "office": item["office"],
                            "election_round": item["election_round"],
                            "candidate_count": item["candidate_count"],
                            "section_count": item["section_count"],
                            "polling_place_count": item["polling_place_count"],
                            "top_candidates": item["top_candidates"],
                        }
                        for item in raw_candidate_scopes[year]["items"]
                    ],
                    "db_offices": [
                        item
                        for item in db_candidate_scopes
                        if int(item["election_year"]) == year
                    ],
                }
                for year in audit_years
            ],
            "api_context_top_candidates_2024": election_context_response["items"],
            "db_top_candidates_for_api_scope_2024": db_top_candidates_api_scope,
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Audit report written to {output_path}")


if __name__ == "__main__":
    main()
