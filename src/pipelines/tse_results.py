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


def _normalize_text(value: str) -> str:
    stripped = value.strip().casefold()
    return "".join(ch for ch in unicodedata.normalize("NFKD", stripped) if not unicodedata.combining(ch))


def _normalize_zone_code(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw.lower() == "nan":
        return None
    try:
        return str(int(float(raw)))
    except (TypeError, ValueError):
        return raw


def _resolve_municipality_context(settings: Settings) -> tuple[str, str, str]:
    with session_scope(settings) as session:
        row = session.execute(
            text(
                """
                SELECT territory_id::text, name, uf
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
    territory_id, name, uf = str(row[0]), str(row[1]).strip(), str(row[2]).strip().upper()
    if not territory_id or not name or not uf:
        raise RuntimeError("Invalid municipality context in dim_territory.")
    return territory_id, name, uf


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


def _resolve_results_package(
    client: HttpClient,
    base_url: str,
    reference_year: int,
) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    warnings: list[str] = []
    candidate_ids = [
        f"resultados-{reference_year}",
        "resultados-2024",
        "resultados-2022",
        "resultados-2020",
        "resultados-2018",
        "resultados-2016",
    ]
    ordered_candidates = list(dict.fromkeys(candidate_ids))
    requested_id = f"resultados-{reference_year}"
    for package_id in ordered_candidates:
        package = _ckan_get_package(client, base_url, package_id)
        if package is None:
            continue
        if package_id != requested_id:
            warnings.append(
                f"CKAN package '{requested_id}' not found; fallback to '{package_id}'."
            )
        return package, package_id, warnings
    return None, None, warnings


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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    target_name = _normalize_text(municipality_name)
    usecols = [
        "ANO_ELEICAO",
        "NR_TURNO",
        "NR_ZONA",
        "SG_UF",
        "NM_MUNICIPIO",
        "DS_CARGO",
        *_METRIC_COLUMN.values(),
    ]
    aggregated_municipality: dict[tuple[int, int, str, str], int] = {}
    aggregated_zone: dict[tuple[int, int, str, str, str], int] = {}
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

                for metric, column_name in _METRIC_COLUMN.items():
                    filtered[column_name] = pd.to_numeric(filtered[column_name], errors="coerce").fillna(0)
                    grouped_municipality = (
                        filtered.groupby(["ANO_ELEICAO", "NR_TURNO", "DS_CARGO"], dropna=False)[column_name]
                        .sum()
                        .reset_index()
                    )
                    for row in grouped_municipality.itertuples(index=False):
                        year = int(float(row.ANO_ELEICAO))
                        round_number = int(float(row.NR_TURNO))
                        office = str(row.DS_CARGO).strip() if row.DS_CARGO is not None else "NAO_INFORMADO"
                        value = int(getattr(row, column_name))
                        if value < 0:
                            continue
                        key = (year, round_number, office, metric)
                        aggregated_municipality[key] = aggregated_municipality.get(key, 0) + value

                    grouped_zone = (
                        filtered.groupby(["ANO_ELEICAO", "NR_TURNO", "DS_CARGO", "NR_ZONA"], dropna=False)[
                            column_name
                        ]
                        .sum()
                        .reset_index()
                    )
                    for row in grouped_zone.itertuples(index=False):
                        zone_code = _normalize_zone_code(row.NR_ZONA)
                        if zone_code is None:
                            continue
                        year = int(float(row.ANO_ELEICAO))
                        round_number = int(float(row.NR_TURNO))
                        office = str(row.DS_CARGO).strip() if row.DS_CARGO is not None else "NAO_INFORMADO"
                        value = int(getattr(row, column_name))
                        if value < 0:
                            continue
                        key = (year, round_number, office, metric, zone_code)
                        aggregated_zone[key] = aggregated_zone.get(key, 0) + value

    municipality_rows = [
        {
            "election_year": year,
            "election_round": round_number,
            "office": office,
            "metric": metric,
            "value": value,
        }
        for (year, round_number, office, metric), value in sorted(aggregated_municipality.items())
    ]
    zone_rows = [
        {
            "election_year": year,
            "election_round": round_number,
            "office": office,
            "metric": metric,
            "value": value,
            "tse_zone": zone_code,
        }
        for (year, round_number, office, metric, zone_code), value in sorted(aggregated_zone.items())
    ]
    parse_info = {
        "csv_name": csv_name,
        "rows_scanned": rows_scanned,
        "rows_filtered": rows_filtered,
        "rows_aggregated_municipality": len(municipality_rows),
        "rows_aggregated_zone": len(zone_rows),
    }
    return municipality_rows, zone_rows, parse_info


def _upsert_electoral_zone(
    *,
    session: Any,
    municipality_territory_id: str,
    municipality_ibge_code: str,
    uf: str,
    zone_code: str,
) -> str:
    row = session.execute(
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
                municipality_ibge_code
            )
            VALUES (
                CAST('electoral_zone' AS silver.territory_level),
                CAST(:parent_territory_id AS uuid),
                :canonical_key,
                'TSE',
                :source_entity_id,
                :ibge_geocode,
                :tse_zone,
                '',
                :name,
                :normalized_name,
                :uf,
                :municipality_ibge_code
            )
            ON CONFLICT (level, ibge_geocode, tse_zone, tse_section, municipality_ibge_code)
            DO UPDATE SET
                parent_territory_id = EXCLUDED.parent_territory_id,
                canonical_key = EXCLUDED.canonical_key,
                source_entity_id = EXCLUDED.source_entity_id,
                name = EXCLUDED.name,
                normalized_name = EXCLUDED.normalized_name,
                uf = EXCLUDED.uf,
                updated_at = NOW()
            RETURNING territory_id::text
            """
        ),
        {
            "parent_territory_id": municipality_territory_id,
            "canonical_key": f"electoral_zone:tse:{municipality_ibge_code}:{zone_code}",
            "source_entity_id": f"{uf}-{municipality_ibge_code}-{zone_code}",
            "ibge_geocode": municipality_ibge_code,
            "tse_zone": zone_code,
            "name": f"Zona {zone_code}",
            "normalized_name": _normalize_text(f"Zona {zone_code}"),
            "uf": uf,
            "municipality_ibge_code": municipality_ibge_code,
        },
    ).first()
    if row is None:
        raise RuntimeError(f"Could not upsert electoral zone {zone_code}.")
    return str(row[0])


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
        territory_id, municipality_name, uf = _resolve_municipality_context(settings)

        package, effective_package_id, package_warnings = _resolve_results_package(
            client,
            settings.tse_ckan_base_url,
            reference_year,
        )
        warnings.extend(package_warnings)
        if package is None:
            raise RuntimeError("Could not resolve results package from TSE CKAN.")
        if effective_package_id is None:
            raise RuntimeError("Could not determine results package identifier.")

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
        parsed_rows_municipality, parsed_rows_zone, parse_info = _extract_rows_from_zip(
            zip_bytes=zip_bytes,
            municipality_name=municipality_name,
            uf=uf,
        )
        extracted_years = sorted(
            {
                int(item["election_year"])
                for item in (*parsed_rows_municipality, *parsed_rows_zone)
                if item.get("election_year") is not None
            }
        )
        if extracted_years and reference_year not in extracted_years:
            warnings.append(
                (
                    f"Requested reference_year={reference_year}, but extracted election years are "
                    f"{', '.join(str(year) for year in extracted_years)}."
                )
            )
        if not parsed_rows_municipality and not parsed_rows_zone:
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
                "rows_extracted": len(parsed_rows_municipality) + len(parsed_rows_zone),
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
        zone_rows_written = 0
        municipality_rows_written = 0
        if parsed_rows_municipality or parsed_rows_zone:
            with session_scope(settings) as session:
                zone_territory_ids: dict[str, str] = {}
                for zone_code in sorted({str(item["tse_zone"]) for item in parsed_rows_zone}):
                    zone_territory_ids[zone_code] = _upsert_electoral_zone(
                        session=session,
                        municipality_territory_id=territory_id,
                        municipality_ibge_code=settings.municipality_ibge_code,
                        uf=uf,
                        zone_code=zone_code,
                    )

                for row in parsed_rows_municipality:
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
                            "territory_id": territory_id,
                            "election_year": row["election_year"],
                            "election_round": row["election_round"],
                            "office": row["office"],
                            "metric": row["metric"],
                            "value": row["value"],
                        },
                    )
                    rows_written += 1
                    municipality_rows_written += 1

                for row in parsed_rows_zone:
                    zone_id = zone_territory_ids.get(str(row["tse_zone"]))
                    if zone_id is None:
                        warnings.append(
                            f"Skipped zone row because territory could not be resolved: {row['tse_zone']}."
                        )
                        continue
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
                            "territory_id": zone_id,
                            "election_year": row["election_year"],
                            "election_round": row["election_round"],
                            "office": row["office"],
                            "metric": row["metric"],
                            "value": row["value"],
                        },
                    )
                    rows_written += 1
                    zone_rows_written += 1

        checks = [
            {
                "name": "ckan_package_resolved",
                "status": "pass",
                "details": f"Package '{effective_package_id}' resolved.",
            },
            {
                "name": "results_rows_extracted",
                "status": "pass" if parsed_rows_municipality or parsed_rows_zone else "warn",
                "details": (
                    f"{len(parsed_rows_municipality)} municipality rows and "
                    f"{len(parsed_rows_zone)} zone rows parsed."
                ),
            },
            {
                "name": "results_rows_loaded",
                "status": "pass" if rows_written > 0 else "warn",
                "details": f"{rows_written} rows upserted into silver.fact_election_result.",
            },
            {
                "name": "results_zone_rows_loaded",
                "status": "pass" if zone_rows_written > 0 else "warn",
                "details": f"{zone_rows_written} zone rows upserted into silver.fact_election_result.",
            },
        ]
        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=reference_period,
            raw_bytes=zip_bytes,
            extension=".zip",
            uri=resource_url,
            territory_scope="municipality",
            dataset_version=effective_package_id,
            checks=checks,
            notes="TSE municipal/zone detail results extraction and Silver upsert for municipality scope.",
            run_id=run_id,
            tables_written=["silver.fact_election_result"],
            rows_written=[{"table": "silver.fact_election_result", "rows": rows_written}],
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
                rows_extracted=len(parsed_rows_municipality) + len(parsed_rows_zone),
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
                    "municipality_rows_written": municipality_rows_written,
                    "zone_rows_written": zone_rows_written,
                },
            )
            replace_pipeline_checks_from_dicts(
                session=session,
                run_id=run_id,
                checks=[
                    {
                        "name": check["name"],
                        "status": check["status"],
                        "details": check["details"],
                    }
                    for check in checks
                ],
            )

        elapsed = time.perf_counter() - started_at
        logger.info(
            "TSE results job finished.",
            run_id=run_id,
            rows_extracted=len(parsed_rows_municipality) + len(parsed_rows_zone),
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "success",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": len(parsed_rows_municipality) + len(parsed_rows_zone),
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
