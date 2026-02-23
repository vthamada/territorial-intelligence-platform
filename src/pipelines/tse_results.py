from __future__ import annotations

import io
import json
import time
import unicodedata
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

JOB_NAME = "tse_results_fetch"
SOURCE = "TSE"
DATASET_NAME = "tse_detalhe_votacao_munzona"
WAVE = "MVP-2"
PACKAGE_SHOW_PATH = "/package_show"

_METRIC_COLUMN = {
    "turnout": "QT_COMPARECIMENTO",
    "abstention": "QT_ABSTENCOES",
    "votes_total": "QT_VOTOS",
    "votes_valid": "QT_TOTAL_VOTOS_VALIDOS",
    "votes_blank": "QT_VOTOS_BRANCOS",
    "votes_null": "QT_TOTAL_VOTOS_NULOS",
}

_OPTIONAL_ZONE_COLUMNS = ("NR_ZONA", "NUM_ZONA", "CD_ZONA")
_OPTIONAL_SECTION_COLUMNS = ("NR_SECAO", "NUM_SECAO", "CD_SECAO")
_OPTIONAL_POLLING_PLACE_COLUMNS = ("NM_LOCAL_VOTACAO", "DS_LOCAL_VOTACAO", "NM_LOCAL")


def _normalize_text(value: str) -> str:
    stripped = value.strip().casefold()
    return "".join(ch for ch in unicodedata.normalize("NFKD", stripped) if not unicodedata.combining(ch))


def _normalize_zone(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw.casefold() in {"nan", "none"}:
        return None
    try:
        as_float = float(raw.replace(",", "."))
    except ValueError:
        pass
    else:
        if as_float.is_integer():
            return str(int(as_float))
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits:
        return str(int(digits))
    return None


def _normalize_section(value: Any) -> str | None:
    return _normalize_zone(value)


def _resolve_municipality_context(settings: Settings) -> tuple[str, str, str, str]:
    with session_scope(settings) as session:
        row = session.execute(
            text(
                """
                SELECT territory_id::text, name, uf, municipality_ibge_code
                FROM silver.dim_territory
                WHERE level = 'municipality'
                  AND municipality_ibge_code = :municipality_ibge_code
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """
            ),
            {"municipality_ibge_code": settings.municipality_ibge_code},
        ).first()
    if row is None:
        raise RuntimeError("Municipality territory not found. Run ibge_admin_fetch first.")
    territory_id = str(row[0])
    name = str(row[1]).strip()
    uf = str(row[2]).strip().upper()
    municipality_ibge_code = str(row[3]).strip()
    if not territory_id or not name or not uf or not municipality_ibge_code:
        raise RuntimeError("Invalid municipality context in dim_territory.")
    return territory_id, name, uf, municipality_ibge_code


def _ckan_get_package(client: HttpClient, base_url: str, package_id: str) -> dict[str, Any] | None:
    url = f"{base_url}{PACKAGE_SHOW_PATH}?id={package_id}"
    try:
        payload = client.get_json(url)
    except Exception:
        return None
    if not isinstance(payload, dict) or not payload.get("success"):
        return None
    result = payload.get("result")
    return result if isinstance(result, dict) else None


def _pick_results_resource(resources: list[dict[str, Any]]) -> dict[str, Any] | None:
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        url = str(resource.get("url", "")).strip().lower()
        name = str(resource.get("name", "")).strip().lower()
        if not url:
            continue
        if "detalhe_votacao_munzona" in url and url.endswith(".zip"):
            return resource
        if "detalhe da apuração por município e zona" in name and "munzona" in url:
            return resource
    return None


def _extract_rows_from_zip(
    *,
    zip_bytes: bytes,
    municipality_name: str,
    uf: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    target_name = _normalize_text(municipality_name)
    base_usecols = [
        "ANO_ELEICAO",
        "NR_TURNO",
        "SG_UF",
        "NM_MUNICIPIO",
        "DS_CARGO",
        *_METRIC_COLUMN.values(),
    ]
    aggregated: dict[tuple[int, int, str, str, str | None, str | None], int] = {}
    section_polling_place: dict[tuple[str, str], str] = {}
    rows_scanned = 0
    rows_filtered = 0
    csv_name = ""
    zone_column: str | None = None
    section_column: str | None = None
    polling_place_column: str | None = None

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
            zone_column = next(
                (column for column in _OPTIONAL_ZONE_COLUMNS if column in available_columns),
                None,
            )
            section_column = next(
                (column for column in _OPTIONAL_SECTION_COLUMNS if column in available_columns),
                None,
            )
            polling_place_column = next(
                (
                    column
                    for column in _OPTIONAL_POLLING_PLACE_COLUMNS
                    if column in available_columns
                ),
                None,
            )

        usecols = list(base_usecols)
        if zone_column is not None:
            usecols.append(zone_column)
        if section_column is not None:
            usecols.append(section_column)
        if polling_place_column is not None:
            usecols.append(polling_place_column)

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
                filtered = filtered.dropna(subset=["ANO_ELEICAO"])
                if filtered.empty:
                    continue

                if zone_column is not None:
                    filtered["__TSE_ZONE__"] = filtered[zone_column].map(_normalize_zone)
                else:
                    filtered["__TSE_ZONE__"] = None
                if section_column is not None:
                    filtered["__TSE_SECTION__"] = filtered[section_column].map(_normalize_section)
                else:
                    filtered["__TSE_SECTION__"] = None
                if polling_place_column is not None:
                    filtered["__POLLING_PLACE__"] = (
                        filtered[polling_place_column].astype(str).str.strip().replace({"": None})
                    )
                else:
                    filtered["__POLLING_PLACE__"] = None

                for _, identity_row in filtered[
                    ["__TSE_ZONE__", "__TSE_SECTION__", "__POLLING_PLACE__"]
                ].iterrows():
                    zone_key = _normalize_zone(identity_row["__TSE_ZONE__"])
                    section_key = _normalize_section(identity_row["__TSE_SECTION__"])
                    polling_place_name = identity_row["__POLLING_PLACE__"]
                    if zone_key is None or section_key is None:
                        continue
                    if polling_place_name is None or pd.isna(polling_place_name):
                        continue
                    normalized_place = str(polling_place_name).strip()
                    if not normalized_place or normalized_place.casefold() == "nan":
                        continue
                    section_polling_place.setdefault((zone_key, section_key), normalized_place)

                for metric, column_name in _METRIC_COLUMN.items():
                    filtered[column_name] = pd.to_numeric(filtered[column_name], errors="coerce").fillna(0)
                    grouped = (
                        filtered.groupby(
                            ["ANO_ELEICAO", "NR_TURNO", "DS_CARGO", "__TSE_ZONE__", "__TSE_SECTION__"],
                            dropna=False,
                        )[column_name]
                        .sum()
                        .reset_index()
                    )
                    for _, grouped_row in grouped.iterrows():
                        year = int(float(grouped_row["ANO_ELEICAO"]))
                        round_number = int(float(grouped_row["NR_TURNO"]))
                        office_raw = grouped_row["DS_CARGO"]
                        office = str(office_raw).strip() if office_raw is not None else "NAO_INFORMADO"
                        tse_zone = _normalize_zone(grouped_row["__TSE_ZONE__"])
                        tse_section = _normalize_section(grouped_row["__TSE_SECTION__"])
                        if tse_zone is None:
                            tse_section = None
                        value = int(grouped_row[column_name])
                        if value < 0:
                            continue
                        key = (year, round_number, office, metric, tse_zone, tse_section)
                        aggregated[key] = aggregated.get(key, 0) + value

    result_rows: list[dict[str, Any]] = []
    for (year, round_number, office, metric, tse_zone, tse_section), value in sorted(
        aggregated.items()
    ):
        polling_place_name = None
        if tse_zone is not None and tse_section is not None:
            polling_place_name = section_polling_place.get((tse_zone, tse_section))
        result_rows.append(
            {
                "election_year": year,
                "election_round": round_number,
                "office": office,
                "metric": metric,
                "value": value,
                "tse_zone": tse_zone,
                "tse_section": tse_section,
                "polling_place_name": polling_place_name,
            }
        )
    zones_detected = sorted(
        {row["tse_zone"] for row in result_rows if row["tse_zone"] is not None},
        key=lambda value: int(value),
    )
    sections_detected = sorted(
        {
            f"{row['tse_zone']}/{row['tse_section']}"
            for row in result_rows
            if row["tse_zone"] is not None and row["tse_section"] is not None
        },
        key=lambda value: tuple(int(part) for part in value.split("/", 1)),
    )
    parse_info = {
        "csv_name": csv_name,
        "rows_scanned": rows_scanned,
        "rows_filtered": rows_filtered,
        "rows_aggregated": len(result_rows),
        "zone_column": zone_column,
        "section_column": section_column,
        "polling_place_column": polling_place_column,
        "zones_detected": zones_detected,
        "sections_detected": sections_detected,
        "polling_places_detected": len(section_polling_place),
    }
    return result_rows, parse_info


def _build_result_checks(
    *,
    package_id: str,
    parsed_rows_count: int,
    rows_written: int,
    zones_detected: int,
    sections_detected: int,
    polling_places_detected: int,
    zones_upserted: int,
    sections_upserted: int,
) -> list[dict[str, Any]]:
    return [
        {
            "name": "ckan_package_resolved",
            "status": "pass",
            "details": f"Package '{package_id}' resolved.",
        },
        {
            "name": "results_rows_extracted",
            "status": "pass" if parsed_rows_count > 0 else "warn",
            "details": f"{parsed_rows_count} results rows parsed for municipality.",
            "observed_value": parsed_rows_count,
            "threshold_value": 1,
        },
        {
            "name": "results_rows_loaded",
            "status": "pass" if rows_written > 0 else "warn",
            "details": f"{rows_written} rows upserted into silver.fact_election_result.",
            "observed_value": rows_written,
            "threshold_value": 1,
        },
        {
            "name": "electoral_zone_keys_detected",
            "status": "pass" if zones_detected > 0 else "warn",
            "details": f"{zones_detected} electoral zone keys detected in source payload.",
            "observed_value": zones_detected,
            "threshold_value": 1,
        },
        {
            "name": "electoral_section_keys_detected",
            "status": "pass" if sections_detected > 0 else "warn",
            "details": f"{sections_detected} electoral section keys detected in source payload.",
            "observed_value": sections_detected,
            "threshold_value": 1,
        },
        {
            "name": "electoral_polling_places_detected",
            "status": "pass" if polling_places_detected > 0 else "warn",
            "details": f"{polling_places_detected} polling place names detected for zone/section keys.",
            "observed_value": polling_places_detected,
            "threshold_value": 1,
        },
        {
            "name": "electoral_zone_rows_detected",
            "status": "pass" if zones_upserted > 0 else "warn",
            "details": f"{zones_upserted} electoral zone territories upserted in silver.dim_territory.",
            "observed_value": zones_upserted,
            "threshold_value": 1,
        },
        {
            "name": "electoral_section_rows_detected",
            "status": "pass" if sections_upserted > 0 else "warn",
            "details": f"{sections_upserted} electoral section territories upserted in silver.dim_territory.",
            "observed_value": sections_upserted,
            "threshold_value": 1,
        },
    ]


def _upsert_electoral_zone_territory(
    *,
    session,
    municipality_territory_id: str,
    municipality_name: str,
    municipality_ibge_code: str,
    uf: str,
    tse_zone: str,
) -> str:
    canonical_key = f"electoral_zone:tse:{uf}:{tse_zone}"
    source_entity_id = f"electoral_zone:{municipality_ibge_code}:{tse_zone}"
    zone_name = f"Zona eleitoral {tse_zone} - {municipality_name}"
    normalized_section = ""
    metadata = {
        "official_status": "proxy",
        "proxy_method": "Geometria herdada do municipio para disponibilizar visualizacao inicial por zona.",
        "source": SOURCE,
        "dataset": DATASET_NAME,
    }
    return str(
        session.execute(
            text(
                """
                INSERT INTO silver.dim_territory (
                    level,
                    parent_territory_id,
                    canonical_key,
                    source_system,
                    source_entity_id,
                    ibge_geocode,
                    tse_zone,
                    tse_section,
                    name,
                    normalized_name,
                    uf,
                    municipality_ibge_code,
                    geometry,
                    metadata
                )
                VALUES (
                    CAST('electoral_zone' AS silver.territory_level),
                    CAST(:parent_territory_id AS uuid),
                    :canonical_key,
                    :source_system,
                    :source_entity_id,
                    :municipality_ibge_code,
                    :tse_zone,
                    :tse_section,
                    :name,
                    :normalized_name,
                    :uf,
                    :municipality_ibge_code,
                    (
                        SELECT geometry
                        FROM silver.dim_territory
                        WHERE territory_id = CAST(:parent_territory_id AS uuid)
                        LIMIT 1
                    ),
                    CAST(:metadata AS jsonb)
                )
                ON CONFLICT (level, ibge_geocode, tse_zone, tse_section, municipality_ibge_code)
                DO UPDATE SET
                    parent_territory_id = EXCLUDED.parent_territory_id,
                    canonical_key = EXCLUDED.canonical_key,
                    source_system = EXCLUDED.source_system,
                    source_entity_id = EXCLUDED.source_entity_id,
                    tse_zone = EXCLUDED.tse_zone,
                    tse_section = EXCLUDED.tse_section,
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    uf = EXCLUDED.uf,
                    geometry = COALESCE(EXCLUDED.geometry, silver.dim_territory.geometry),
                    metadata = COALESCE(silver.dim_territory.metadata, '{}'::jsonb) || EXCLUDED.metadata,
                    updated_at = NOW()
                RETURNING territory_id::text
                """
            ),
            {
                "parent_territory_id": municipality_territory_id,
                "canonical_key": canonical_key,
                "source_system": SOURCE,
                "source_entity_id": source_entity_id,
                "tse_zone": tse_zone,
                "tse_section": normalized_section,
                "name": zone_name,
                "normalized_name": _normalize_text(zone_name),
                "uf": uf,
                "municipality_ibge_code": municipality_ibge_code,
                "metadata": json.dumps(metadata),
            },
        ).scalar_one()
    )


def _upsert_electoral_section_territory(
    *,
    session,
    zone_territory_id: str,
    municipality_name: str,
    municipality_ibge_code: str,
    uf: str,
    tse_zone: str,
    tse_section: str,
    polling_place_name: str | None = None,
) -> str:
    canonical_key = f"electoral_section:tse:{uf}:{tse_zone}:{tse_section}"
    source_entity_id = f"electoral_section:{municipality_ibge_code}:{tse_zone}:{tse_section}"
    section_name = f"Secao eleitoral {tse_section} (zona {tse_zone}) - {municipality_name}"
    metadata = {
        "official_status": "proxy",
        "proxy_method": "Secao agregada em ponto representativo da geometria da zona eleitoral.",
        "source": SOURCE,
        "dataset": DATASET_NAME,
    }
    if polling_place_name:
        metadata["polling_place_name"] = polling_place_name
    return str(
        session.execute(
            text(
                """
                INSERT INTO silver.dim_territory (
                    level,
                    parent_territory_id,
                    canonical_key,
                    source_system,
                    source_entity_id,
                    ibge_geocode,
                    tse_zone,
                    tse_section,
                    name,
                    normalized_name,
                    uf,
                    municipality_ibge_code,
                    geometry,
                    metadata
                )
                VALUES (
                    CAST('electoral_section' AS silver.territory_level),
                    CAST(:parent_territory_id AS uuid),
                    :canonical_key,
                    :source_system,
                    :source_entity_id,
                    NULL,
                    :tse_zone,
                    :tse_section,
                    :name,
                    :normalized_name,
                    :uf,
                    :municipality_ibge_code,
                    (
                        SELECT
                            CASE
                                WHEN geometry IS NULL THEN NULL
                                ELSE ST_PointOnSurface(geometry)
                            END
                        FROM silver.dim_territory
                        WHERE territory_id = CAST(:parent_territory_id AS uuid)
                        LIMIT 1
                    ),
                    CAST(:metadata AS jsonb)
                )
                ON CONFLICT (source_system, source_entity_id, municipality_ibge_code)
                DO UPDATE SET
                    parent_territory_id = EXCLUDED.parent_territory_id,
                    canonical_key = EXCLUDED.canonical_key,
                    tse_zone = EXCLUDED.tse_zone,
                    tse_section = EXCLUDED.tse_section,
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    uf = EXCLUDED.uf,
                    geometry = COALESCE(EXCLUDED.geometry, silver.dim_territory.geometry),
                    metadata = COALESCE(silver.dim_territory.metadata, '{}'::jsonb) || EXCLUDED.metadata,
                    updated_at = NOW()
                RETURNING territory_id::text
                """
            ),
            {
                "parent_territory_id": zone_territory_id,
                "canonical_key": canonical_key,
                "source_system": SOURCE,
                "source_entity_id": source_entity_id,
                "tse_zone": tse_zone,
                "tse_section": tse_section,
                "name": section_name,
                "normalized_name": _normalize_text(section_name),
                "uf": uf,
                "municipality_ibge_code": municipality_ibge_code,
                "metadata": json.dumps(metadata),
            },
        ).scalar_one()
    )


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
        territory_id, municipality_name, uf, municipality_ibge_code = _resolve_municipality_context(
            settings
        )

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
            raise RuntimeError("Could not resolve results package from TSE CKAN.")

        resources = package.get("resources", [])
        if not isinstance(resources, list):
            raise RuntimeError("Invalid resources format in TSE CKAN package.")
        resource = _pick_results_resource(resources)
        if resource is None:
            raise RuntimeError("No munzona detail resource found in TSE CKAN package.")

        resource_url = str(resource.get("url", "")).strip()
        if not resource_url:
            raise RuntimeError("Selected TSE results resource has empty URL.")

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
        if not parsed_rows:
            warnings.append(
                f"No results rows found for municipality '{municipality_name}' ({uf}) in selected resource."
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
                                )
                            target_territory_id = section_to_territory_id[section_key]

                    session.execute(
                        text(
                            """
                            INSERT INTO silver.fact_election_result (
                                territory_id,
                                election_year,
                                election_round,
                                office,
                                metric,
                                value
                            )
                            VALUES (
                                CAST(:territory_id AS uuid),
                                :election_year,
                                :election_round,
                                :office,
                                :metric,
                                :value
                            )
                            ON CONFLICT (
                                territory_id,
                                election_year,
                                election_round,
                                office,
                                metric
                            )
                            DO UPDATE SET
                                value = EXCLUDED.value
                            """
                        ),
                        {
                            "territory_id": target_territory_id,
                            "election_year": row["election_year"],
                            "election_round": row["election_round"],
                            "office": row["office"],
                            "metric": row["metric"],
                            "value": row["value"],
                        },
                    )
                    rows_written += 1
                zones_upserted = len(zone_to_territory_id)
                sections_upserted = len(section_to_territory_id)

        checks = _build_result_checks(
            package_id=effective_package_id,
            parsed_rows_count=len(parsed_rows),
            rows_written=rows_written,
            zones_detected=len(parse_info.get("zones_detected", [])),
            sections_detected=len(parse_info.get("sections_detected", [])),
            polling_places_detected=int(parse_info.get("polling_places_detected", 0)),
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
            notes="TSE municipal/zone detail results extraction and Silver upsert for municipality and electoral zone scope.",
            run_id=run_id,
            tables_written=["silver.fact_election_result", "silver.dim_territory"],
            rows_written=[
                {"table": "silver.fact_election_result", "rows": rows_written},
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
            replace_pipeline_checks_from_dicts(
                session=session,
                run_id=run_id,
                checks=checks,
            )

        elapsed = time.perf_counter() - started_at
        logger.info(
            "TSE results job finished.",
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
            "TSE results job failed.",
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
