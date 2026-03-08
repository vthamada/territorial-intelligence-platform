from __future__ import annotations

import io
import json
import time
import zipfile
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pandas as pd
from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run
from pipelines.tse_results import (
    _OPTIONAL_POLLING_PLACE_COLUMNS,
    _OPTIONAL_POLLING_PLACE_ADDRESS_COLUMNS,
    _OPTIONAL_POLLING_PLACE_CODE_COLUMNS,
    _OPTIONAL_SECTION_COLUMNS,
    _OPTIONAL_ZONE_COLUMNS,
    _ckan_get_package,
    _normalize_section,
    _normalize_text,
    _normalize_zone,
    _resolve_municipality_context,
    _upsert_electoral_section_territory,
    _upsert_electoral_zone_territory,
)

JOB_NAME = "tse_candidate_votes_fetch"
SOURCE = "TSE"
DATASET_NAME = "tse_votacao_secao"
WAVE = "MVP-2"

_CANDIDATE_NAME_COLUMNS = ("NM_URNA_CANDIDATO", "NM_VOTAVEL", "NM_CANDIDATO")
_BALLOT_NAME_COLUMNS = ("NM_URNA_CANDIDATO", "NM_VOTAVEL")
_FULL_NAME_COLUMNS = ("NM_CANDIDATO", "NM_VOTAVEL")
_CANDIDATE_NUMBER_COLUMNS = ("NR_VOTAVEL", "NR_CANDIDATO")
_PARTY_ABBR_COLUMNS = ("SG_PARTIDO",)
_PARTY_NUMBER_COLUMNS = ("NR_PARTIDO",)
_PARTY_NAME_COLUMNS = ("NM_PARTIDO",)
_VOTE_COLUMNS = ("QT_VOTOS_NOMINAIS", "QT_VOTOS", "QT_VOTOS_VALIDOS")


def _pick_candidate_votes_resource(
    resources: list[dict[str, Any]],
    *,
    uf: str,
) -> dict[str, Any] | None:
    normalized_uf = uf.strip().upper()
    exact_matches: list[dict[str, Any]] = []
    generic_matches: list[dict[str, Any]] = []

    for resource in resources:
        if not isinstance(resource, dict):
            continue
        url = str(resource.get("url", "")).strip().lower()
        name = _normalize_text(str(resource.get("name", "")))
        if not url:
            continue
        if "votacao_secao" not in url or not url.endswith(".zip"):
            continue
        resource_copy = dict(resource)
        if url.endswith(f"_{normalized_uf.lower()}.zip") or f" {normalized_uf.lower()} " in f" {name} ":
            exact_matches.append(resource_copy)
            continue
        if url.endswith("_br.zip") or url.endswith("_brasil.zip"):
            generic_matches.append(resource_copy)

    if exact_matches:
        return exact_matches[0]
    if generic_matches:
        return generic_matches[0]
    return None


def _pick_first_available(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    return next((column for column in candidates if column in columns), None)


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value or text_value.casefold() in {"nan", "none"}:
        return None
    return text_value


def _normalize_candidate_number(value: Any) -> str | None:
    normalized = _normalize_zone(value)
    if normalized is not None:
        return normalized
    return _normalize_optional_text(value)


def _derive_election_type(office: str) -> str:
    normalized = _normalize_text(office)
    if normalized in {"prefeito", "vereador", "vice-prefeito"}:
        return "municipal"
    if normalized in {
        "presidente",
        "governador",
        "senador",
        "deputado federal",
        "deputado estadual",
        "deputado distrital",
    }:
        return "general"
    return "other"


def _extract_rows_from_zip(
    *,
    zip_bytes: bytes,
    municipality_name: str,
    uf: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    target_name = _normalize_text(municipality_name)
    rows_scanned = 0
    rows_filtered = 0
    csv_name = ""

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        csv_files = [name for name in archive.namelist() if name.lower().endswith(f"_{uf.lower()}.csv")]
        if not csv_files:
            csv_files = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_files:
            raise ValueError("Zip payload has no CSV file.")
        csv_name = csv_files[0]

        with archive.open(csv_name) as csv_bytes:
            wrapper = io.TextIOWrapper(csv_bytes, encoding="latin1", newline="")
            header_df = pd.read_csv(wrapper, sep=";", nrows=0, low_memory=False)
            available_columns = [str(column) for column in header_df.columns]

        zone_column = _pick_first_available(available_columns, _OPTIONAL_ZONE_COLUMNS)
        section_column = _pick_first_available(available_columns, _OPTIONAL_SECTION_COLUMNS)
        polling_place_column = _pick_first_available(available_columns, _OPTIONAL_POLLING_PLACE_COLUMNS)
        polling_place_code_column = _pick_first_available(
            available_columns, _OPTIONAL_POLLING_PLACE_CODE_COLUMNS
        )
        polling_place_address_column = _pick_first_available(
            available_columns, _OPTIONAL_POLLING_PLACE_ADDRESS_COLUMNS
        )
        candidate_name_column = _pick_first_available(available_columns, _CANDIDATE_NAME_COLUMNS)
        ballot_name_column = _pick_first_available(available_columns, _BALLOT_NAME_COLUMNS)
        full_name_column = _pick_first_available(available_columns, _FULL_NAME_COLUMNS)
        candidate_number_column = _pick_first_available(available_columns, _CANDIDATE_NUMBER_COLUMNS)
        party_abbr_column = _pick_first_available(available_columns, _PARTY_ABBR_COLUMNS)
        party_number_column = _pick_first_available(available_columns, _PARTY_NUMBER_COLUMNS)
        party_name_column = _pick_first_available(available_columns, _PARTY_NAME_COLUMNS)
        votes_column = _pick_first_available(available_columns, _VOTE_COLUMNS)

        if candidate_name_column is None or candidate_number_column is None or votes_column is None:
            raise ValueError("Candidate vote CSV missing required candidate/vote columns.")

        usecols = [
            "ANO_ELEICAO",
            "NR_TURNO",
            "SG_UF",
            "NM_MUNICIPIO",
            "DS_CARGO",
            candidate_name_column,
            candidate_number_column,
            votes_column,
        ]
        for optional_column in (
            zone_column,
            section_column,
            polling_place_column,
            polling_place_code_column,
            polling_place_address_column,
            ballot_name_column,
            full_name_column,
            party_abbr_column,
            party_number_column,
            party_name_column,
        ):
            if optional_column and optional_column not in usecols:
                usecols.append(optional_column)

        aggregated: dict[
            tuple[
                int,
                int,
                str,
                str | None,
                str | None,
                str,
                str,
                str | None,
                str | None,
                str | None,
                str | None,
                str | None,
                str | None,
                str | None,
                str | None,
            ],
            int,
        ] = {}

        with archive.open(csv_name) as csv_bytes:
            wrapper = io.TextIOWrapper(csv_bytes, encoding="latin1", newline="")
            chunks = pd.read_csv(
                wrapper,
                sep=";",
                usecols=usecols,
                chunksize=200_000,
                low_memory=False,
            )
            for chunk in chunks:
                rows_scanned += len(chunk)
                filtered = chunk[
                    chunk["SG_UF"].astype(str).str.strip().str.upper().eq(uf)
                    & chunk["NM_MUNICIPIO"].astype(str).map(_normalize_text).eq(target_name)
                ].copy()
                if filtered.empty:
                    continue
                rows_filtered += len(filtered)

                filtered["ANO_ELEICAO"] = pd.to_numeric(filtered["ANO_ELEICAO"], errors="coerce")
                filtered["NR_TURNO"] = pd.to_numeric(filtered["NR_TURNO"], errors="coerce").fillna(0)
                filtered[votes_column] = pd.to_numeric(filtered[votes_column], errors="coerce").fillna(0)
                filtered = filtered.dropna(subset=["ANO_ELEICAO"])
                if filtered.empty:
                    continue

                filtered["__TSE_ZONE__"] = filtered[zone_column].map(_normalize_zone) if zone_column else None
                filtered["__TSE_SECTION__"] = (
                    filtered[section_column].map(_normalize_section) if section_column else None
                )
                filtered["__POLLING_PLACE__"] = (
                    filtered[polling_place_column].map(_normalize_optional_text)
                    if polling_place_column
                    else None
                )
                filtered["__POLLING_PLACE_CODE__"] = (
                    filtered[polling_place_code_column].map(_normalize_zone)
                    if polling_place_code_column
                    else None
                )
                filtered["__POLLING_PLACE_ADDRESS__"] = (
                    filtered[polling_place_address_column].map(_normalize_optional_text)
                    if polling_place_address_column
                    else None
                )
                filtered["__CANDIDATE_NAME__"] = filtered[candidate_name_column].map(_normalize_optional_text)
                filtered["__BALLOT_NAME__"] = (
                    filtered[ballot_name_column].map(_normalize_optional_text)
                    if ballot_name_column
                    else None
                )
                filtered["__FULL_NAME__"] = (
                    filtered[full_name_column].map(_normalize_optional_text)
                    if full_name_column
                    else None
                )
                filtered["__CANDIDATE_NUMBER__"] = filtered[candidate_number_column].map(
                    _normalize_candidate_number
                )
                filtered["__PARTY_ABBR__"] = (
                    filtered[party_abbr_column].map(_normalize_optional_text)
                    if party_abbr_column
                    else None
                )
                filtered["__PARTY_NUMBER__"] = (
                    filtered[party_number_column].map(_normalize_candidate_number)
                    if party_number_column
                    else None
                )
                filtered["__PARTY_NAME__"] = (
                    filtered[party_name_column].map(_normalize_optional_text)
                    if party_name_column
                    else None
                )
                filtered = filtered[
                    filtered["__CANDIDATE_NAME__"].notna() & filtered["__CANDIDATE_NUMBER__"].notna()
                ]
                if filtered.empty:
                    continue

                group_columns = [
                    "ANO_ELEICAO",
                    "NR_TURNO",
                    "DS_CARGO",
                    "__TSE_ZONE__",
                    "__TSE_SECTION__",
                    "__POLLING_PLACE__",
                    "__CANDIDATE_NUMBER__",
                    "__CANDIDATE_NAME__",
                    "__BALLOT_NAME__",
                    "__FULL_NAME__",
                    "__PARTY_ABBR__",
                    "__PARTY_NUMBER__",
                    "__PARTY_NAME__",
                    "__POLLING_PLACE_CODE__",
                    "__POLLING_PLACE_ADDRESS__",
                ]
                grouped = filtered.groupby(group_columns, dropna=False)[votes_column].sum().reset_index()

                for _, grouped_row in grouped.iterrows():
                    votes = int(grouped_row[votes_column])
                    if votes < 0:
                        continue
                    office = _normalize_optional_text(grouped_row["DS_CARGO"]) or "NAO_INFORMADO"
                    key = (
                        int(float(grouped_row["ANO_ELEICAO"])),
                        int(float(grouped_row["NR_TURNO"])),
                        office,
                        _normalize_zone(grouped_row["__TSE_ZONE__"]),
                        _normalize_section(grouped_row["__TSE_SECTION__"]),
                        str(grouped_row["__CANDIDATE_NUMBER__"]),
                        str(grouped_row["__CANDIDATE_NAME__"]),
                        _normalize_optional_text(grouped_row["__BALLOT_NAME__"]),
                        _normalize_optional_text(grouped_row["__FULL_NAME__"]),
                        _normalize_optional_text(grouped_row["__PARTY_ABBR__"]),
                        _normalize_optional_text(grouped_row["__PARTY_NUMBER__"]),
                        _normalize_optional_text(grouped_row["__PARTY_NAME__"]),
                        _normalize_optional_text(grouped_row["__POLLING_PLACE__"]),
                        _normalize_zone(grouped_row["__POLLING_PLACE_CODE__"]),
                        _normalize_optional_text(grouped_row["__POLLING_PLACE_ADDRESS__"]),
                    )
                    aggregated[key] = aggregated.get(key, 0) + votes

    result_rows: list[dict[str, Any]] = []
    for (
        year,
        round_number,
        office,
        tse_zone,
        tse_section,
        candidate_number,
        candidate_name,
        ballot_name,
        full_name,
        party_abbr,
        party_number,
        party_name,
        polling_place_name,
        polling_place_code,
        polling_place_address,
    ), votes in sorted(aggregated.items()):
        result_rows.append(
            {
                "election_year": year,
                "election_round": round_number,
                "office": office,
                "election_type": _derive_election_type(office),
                "tse_zone": tse_zone,
                "tse_section": tse_section,
                "polling_place_name": polling_place_name,
                "polling_place_code": polling_place_code,
                "polling_place_address": polling_place_address,
                "candidate_number": candidate_number,
                "candidate_name": candidate_name,
                "ballot_name": ballot_name,
                "full_name": full_name,
                "party_abbr": party_abbr,
                "party_number": party_number,
                "party_name": party_name,
                "votes": votes,
            }
        )

    parse_info = {
        "csv_name": csv_name,
        "rows_scanned": rows_scanned,
        "rows_filtered": rows_filtered,
        "rows_aggregated": len(result_rows),
        "zones_detected": len({row["tse_zone"] for row in result_rows if row["tse_zone"] is not None}),
        "sections_detected": len(
            {
                (row["tse_zone"], row["tse_section"])
                for row in result_rows
                if row["tse_zone"] is not None and row["tse_section"] is not None
            }
        ),
        "polling_places_detected": len(
            {row["polling_place_name"] for row in result_rows if row["polling_place_name"]}
        ),
        "candidates_detected": len(
            {(row["election_year"], row["office"], row["candidate_number"]) for row in result_rows}
        ),
    }
    return result_rows, parse_info


def _upsert_election(
    *,
    session,
    election_year: int,
    election_round: int | None,
    office: str,
    election_type: str,
) -> str:
    return str(
        session.execute(
            text(
                """
                INSERT INTO silver.dim_election (
                    election_year,
                    election_round,
                    office,
                    election_type
                ) VALUES (
                    :election_year,
                    :election_round,
                    :office,
                    :election_type
                )
                ON CONFLICT (election_year, election_round, office)
                DO UPDATE SET
                    election_type = EXCLUDED.election_type,
                    updated_at = NOW()
                RETURNING election_id::text
                """
            ),
            {
                "election_year": election_year,
                "election_round": election_round,
                "office": office,
                "election_type": election_type,
            },
        ).scalar_one()
    )


def _upsert_candidate(
    *,
    session,
    election_id: str,
    candidate_number: str,
    candidate_name: str,
    ballot_name: str | None,
    full_name: str | None,
    party_abbr: str | None,
    party_number: str | None,
    party_name: str | None,
) -> str:
    metadata = {"full_name": full_name} if full_name else {}
    return str(
        session.execute(
            text(
                """
                INSERT INTO silver.dim_candidate (
                    election_id,
                    candidate_number,
                    candidate_name,
                    ballot_name,
                    party_abbr,
                    party_number,
                    party_name,
                    metadata
                ) VALUES (
                    CAST(:election_id AS uuid),
                    :candidate_number,
                    :candidate_name,
                    :ballot_name,
                    :party_abbr,
                    :party_number,
                    :party_name,
                    CAST(:metadata AS jsonb)
                )
                ON CONFLICT (election_id, candidate_number)
                DO UPDATE SET
                    candidate_name = EXCLUDED.candidate_name,
                    ballot_name = COALESCE(EXCLUDED.ballot_name, silver.dim_candidate.ballot_name),
                    party_abbr = COALESCE(EXCLUDED.party_abbr, silver.dim_candidate.party_abbr),
                    party_number = COALESCE(EXCLUDED.party_number, silver.dim_candidate.party_number),
                    party_name = COALESCE(EXCLUDED.party_name, silver.dim_candidate.party_name),
                    metadata = COALESCE(silver.dim_candidate.metadata, '{}'::jsonb) || EXCLUDED.metadata,
                    updated_at = NOW()
                RETURNING candidate_id::text
                """
            ),
            {
                "election_id": election_id,
                "candidate_number": candidate_number,
                "candidate_name": candidate_name,
                "ballot_name": ballot_name,
                "party_abbr": party_abbr,
                "party_number": party_number,
                "party_name": party_name,
                "metadata": json.dumps(metadata),
            },
        ).scalar_one()
    )


def _build_checks(
    *,
    package_id: str,
    parsed_rows_count: int,
    rows_written: int,
    candidates_detected: int,
    zones_upserted: int,
    sections_upserted: int,
) -> list[dict[str, Any]]:
    return [
        {"name": "ckan_package_resolved", "status": "pass", "details": f"Package '{package_id}' resolved."},
        {
            "name": "candidate_vote_rows_extracted",
            "status": "pass" if parsed_rows_count > 0 else "warn",
            "details": f"{parsed_rows_count} candidate vote rows parsed for municipality.",
            "observed_value": parsed_rows_count,
            "threshold_value": 1,
        },
        {
            "name": "candidate_vote_rows_loaded",
            "status": "pass" if rows_written > 0 else "warn",
            "details": f"{rows_written} rows upserted into silver.fact_candidate_vote.",
            "observed_value": rows_written,
            "threshold_value": 1,
        },
        {
            "name": "candidate_entities_detected",
            "status": "pass" if candidates_detected > 0 else "warn",
            "details": f"{candidates_detected} unique candidates detected in payload.",
            "observed_value": candidates_detected,
            "threshold_value": 1,
        },
        {
            "name": "candidate_vote_zone_rows_detected",
            "status": "pass" if zones_upserted > 0 else "warn",
            "details": f"{zones_upserted} electoral zone territories ensured for candidate payload.",
            "observed_value": zones_upserted,
            "threshold_value": 1,
        },
        {
            "name": "candidate_vote_section_rows_detected",
            "status": "pass" if sections_upserted > 0 else "warn",
            "details": f"{sections_upserted} electoral section territories ensured for candidate payload.",
            "observed_value": sections_upserted,
            "threshold_value": 1,
        },
    ]


def run(
    *,
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
    settings: Settings | None = None,
) -> dict[str, Any]:
    del force
    settings = settings or get_settings()
    logger = get_logger(JOB_NAME)
    run_id = str(uuid4())
    started_at_utc = datetime.now(UTC)
    started_at = time.perf_counter()
    warnings: list[str] = []

    client = HttpClient.from_settings(
        settings,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )

    try:
        reference_year = int(reference_period)
    except ValueError:
        return {
            "job": JOB_NAME,
            "status": "failed",
            "run_id": run_id,
            "duration_seconds": 0.0,
            "rows_extracted": 0,
            "rows_written": 0,
            "warnings": warnings,
            "errors": [f"Invalid reference_period '{reference_period}'. Expected year (YYYY)."],
        }

    try:
        territory_id, municipality_name, uf, municipality_ibge_code = _resolve_municipality_context(settings)
        package_id = f"resultados-{reference_year}"
        package = _ckan_get_package(client, settings.tse_ckan_base_url, package_id)
        effective_package_id = package_id
        if package is None:
            for fallback in ("resultados-2024", "resultados-2022", "resultados-2020"):
                package = _ckan_get_package(client, settings.tse_ckan_base_url, fallback)
                if package is not None:
                    effective_package_id = fallback
                    warnings.append(
                        f"CKAN package '{package_id}' not found; fallback to '{effective_package_id}'."
                    )
                    break
        if package is None:
            raise RuntimeError("Could not resolve candidate vote package from TSE CKAN.")

        resources = package.get("resources", [])
        if not isinstance(resources, list):
            raise RuntimeError("Invalid resources format in TSE CKAN package.")
        resource = _pick_candidate_votes_resource(resources, uf=uf)
        if resource is None:
            raise RuntimeError("No candidate vote section resource found in TSE CKAN package.")

        resource_url = str(resource.get("url", "")).strip()
        if not resource_url:
            raise RuntimeError("Selected TSE candidate votes resource has empty URL.")

        zip_bytes, _ = client.download_bytes(
            resource_url,
            expected_content_types=["zip", "octet-stream", "application/octet-stream"],
            min_bytes=1024,
        )
        parsed_rows, parse_info = _extract_rows_from_zip(
            zip_bytes=zip_bytes,
            municipality_name=municipality_name,
            uf=uf,
        )

        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": JOB_NAME,
                "status": "success",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": len(parsed_rows),
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "preview": {
                    "package_id": effective_package_id,
                    "resource_url": resource_url,
                    "parse_info": parse_info,
                },
            }

        rows_written = 0
        zones_upserted = 0
        sections_upserted = 0
        if parsed_rows:
            with session_scope(settings) as session:
                zone_to_territory_id: dict[str, str] = {}
                section_to_territory_id: dict[tuple[str, str], str] = {}
                election_to_id: dict[tuple[int, int, str], str] = {}
                candidate_to_id: dict[tuple[str, str], str] = {}

                for row in parsed_rows:
                    target_territory_id = territory_id
                    tse_zone = row.get("tse_zone")
                    if tse_zone is not None:
                        if tse_zone not in zone_to_territory_id:
                            zone_to_territory_id[tse_zone] = _upsert_electoral_zone_territory(
                                session=session,
                                municipality_territory_id=territory_id,
                                municipality_name=municipality_name,
                                municipality_ibge_code=municipality_ibge_code,
                                uf=uf,
                                tse_zone=tse_zone,
                            )
                        target_territory_id = zone_to_territory_id[tse_zone]

                        tse_section = row.get("tse_section")
                        if tse_section is not None:
                            section_key = (tse_zone, tse_section)
                            if section_key not in section_to_territory_id:
                                section_to_territory_id[section_key] = _upsert_electoral_section_territory(
                                    session=session,
                                    zone_territory_id=target_territory_id,
                                    municipality_name=municipality_name,
                                    municipality_ibge_code=municipality_ibge_code,
                                    uf=uf,
                                    tse_zone=tse_zone,
                                    tse_section=tse_section,
                                    polling_place_name=row.get("polling_place_name"),
                                    polling_place_code=row.get("polling_place_code"),
                                    polling_place_address=row.get("polling_place_address"),
                                )
                            target_territory_id = section_to_territory_id[section_key]

                    election_key = (
                        int(row["election_year"]),
                        int(row["election_round"]),
                        str(row["office"]),
                    )
                    if election_key not in election_to_id:
                        election_to_id[election_key] = _upsert_election(
                            session=session,
                            election_year=election_key[0],
                            election_round=election_key[1],
                            office=election_key[2],
                            election_type=str(row["election_type"]),
                        )
                    election_id = election_to_id[election_key]

                    candidate_key = (election_id, str(row["candidate_number"]))
                    if candidate_key not in candidate_to_id:
                        candidate_to_id[candidate_key] = _upsert_candidate(
                            session=session,
                            election_id=election_id,
                            candidate_number=str(row["candidate_number"]),
                            candidate_name=str(row["candidate_name"]),
                            ballot_name=row.get("ballot_name"),
                            full_name=row.get("full_name"),
                            party_abbr=row.get("party_abbr"),
                            party_number=row.get("party_number"),
                            party_name=row.get("party_name"),
                        )
                    candidate_id = candidate_to_id[candidate_key]

                    session.execute(
                        text(
                            """
                            INSERT INTO silver.fact_candidate_vote (
                                territory_id,
                                election_id,
                                candidate_id,
                                votes
                            )
                            VALUES (
                                CAST(:territory_id AS uuid),
                                CAST(:election_id AS uuid),
                                CAST(:candidate_id AS uuid),
                                :votes
                            )
                            ON CONFLICT (territory_id, election_id, candidate_id)
                            DO UPDATE SET
                                votes = EXCLUDED.votes
                            """
                        ),
                        {
                            "territory_id": target_territory_id,
                            "election_id": election_id,
                            "candidate_id": candidate_id,
                            "votes": int(row["votes"]),
                        },
                    )
                    rows_written += 1

                zones_upserted = len(zone_to_territory_id)
                sections_upserted = len(section_to_territory_id)

        checks = _build_checks(
            package_id=effective_package_id,
            parsed_rows_count=len(parsed_rows),
            rows_written=rows_written,
            candidates_detected=int(parse_info.get("candidates_detected", 0)),
            zones_upserted=zones_upserted,
            sections_upserted=sections_upserted,
        )
        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=reference_period,
            raw_bytes=zip_bytes,
            extension=".zip",
            uri=resource_url,
            territory_scope="municipality,electoral_zone,electoral_section",
            dataset_version=effective_package_id,
            checks=checks,
            notes="TSE candidate vote extraction and Silver upsert for election/candidate/territory vote facts.",
            run_id=run_id,
            tables_written=[
                "silver.dim_election",
                "silver.dim_candidate",
                "silver.fact_candidate_vote",
                "silver.dim_territory",
            ],
            rows_written=[
                {"table": "silver.fact_candidate_vote", "rows": rows_written},
                {"table": "silver.dim_territory", "rows": zones_upserted + sections_upserted},
            ],
        )

        finished_at_utc = datetime.now(UTC)
        with session_scope(settings) as session:
            upsert_pipeline_run(
                session=session,
                run_id=run_id,
                job_name=JOB_NAME,
                source=SOURCE,
                dataset=DATASET_NAME,
                wave=WAVE,
                reference_period=reference_period,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
                status="success",
                rows_extracted=len(parsed_rows),
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "package_id": effective_package_id,
                    "resource_url": resource_url,
                    "parse_info": parse_info,
                    "zones_upserted": zones_upserted,
                    "sections_upserted": sections_upserted,
                },
            )
            replace_pipeline_checks_from_dicts(session=session, run_id=run_id, checks=checks)

        elapsed = time.perf_counter() - started_at
        logger.info(
            "TSE candidate votes job finished.",
            run_id=run_id,
            rows_extracted=len(parsed_rows),
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "success",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": len(parsed_rows),
            "rows_written": rows_written,
            "warnings": warnings,
            "errors": [],
            "bronze": artifact_to_dict(artifact),
        }
    except Exception as exc:  # pragma: no cover - runtime logging path
        elapsed = time.perf_counter() - started_at
        if not dry_run:
            try:
                with session_scope(settings) as session:
                    upsert_pipeline_run(
                        session=session,
                        run_id=run_id,
                        job_name=JOB_NAME,
                        source=SOURCE,
                        dataset=DATASET_NAME,
                        wave=WAVE,
                        reference_period=reference_period,
                        started_at_utc=started_at_utc,
                        finished_at_utc=datetime.now(UTC),
                        status="failed",
                        rows_extracted=0,
                        rows_loaded=0,
                        warnings_count=len(warnings),
                        errors_count=1,
                        details={"error": str(exc)},
                    )
            except Exception:
                logger.exception("Could not persist failed pipeline run in ops tables.", run_id=run_id)

        logger.exception(
            "TSE candidate votes job failed.",
            run_id=run_id,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "failed",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": 0,
            "rows_written": 0,
            "warnings": warnings,
            "errors": [str(exc)],
        }
    finally:
        client.close()
