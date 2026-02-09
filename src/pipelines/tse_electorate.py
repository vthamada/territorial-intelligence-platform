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

JOB_NAME = "tse_electorate_fetch"
SOURCE = "TSE"
DATASET_NAME = "tse_perfil_eleitorado"
WAVE = "MVP-2"
PACKAGE_SHOW_PATH = "/package_show"


def _normalize_text(value: str) -> str:
    stripped = value.strip().casefold()
    return "".join(ch for ch in unicodedata.normalize("NFKD", stripped) if not unicodedata.combining(ch))


def _safe_dimension(value: Any) -> str:
    raw = "" if value is None else str(value).strip()
    return raw if raw else "NAO_INFORMADO"


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
    if not territory_id:
        raise RuntimeError("Municipality territory_id is empty.")
    if not name:
        raise RuntimeError("Municipality name is empty in dim_territory.")
    if not uf:
        raise RuntimeError("Municipality UF is empty in dim_territory.")
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


def _pick_electorate_resource(resources: list[dict[str, Any]]) -> dict[str, Any] | None:
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        url = str(resource.get("url", "")).strip()
        name = str(resource.get("name", "")).strip().lower()
        if not url:
            continue
        if "perfil_eleitorado" in url and url.lower().endswith(".zip") and "local_votacao" not in url:
            return resource
        if "eleitorado -" in name and "local de votação" not in name and "deficiência" not in name:
            return resource
    return None


def _extract_rows_from_zip(
    *,
    zip_bytes: bytes,
    municipality_name: str,
    uf: str,
    requested_year: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    target_name = _normalize_text(municipality_name)
    usecols = [
        "ANO_ELEICAO",
        "SG_UF",
        "NM_MUNICIPIO",
        "DS_GENERO",
        "DS_FAIXA_ETARIA",
        "DS_GRAU_ESCOLARIDADE",
        "QT_ELEITORES_PERFIL",
    ]
    aggregated: dict[tuple[int, str, str, str], int] = {}
    csv_name = ""
    rows_scanned = 0
    rows_filtered = 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
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
                ]
                if filtered.empty:
                    continue

                filtered = filtered.copy()
                filtered["ANO_ELEICAO"] = pd.to_numeric(filtered["ANO_ELEICAO"], errors="coerce")
                filtered["QT_ELEITORES_PERFIL"] = pd.to_numeric(
                    filtered["QT_ELEITORES_PERFIL"],
                    errors="coerce",
                ).fillna(0)
                filtered = filtered[filtered["QT_ELEITORES_PERFIL"] >= 0]
                filtered = filtered.dropna(subset=["ANO_ELEICAO"])
                if filtered.empty:
                    continue

                rows_filtered += len(filtered)
                grouped = (
                    filtered.groupby(
                        ["ANO_ELEICAO", "DS_GENERO", "DS_FAIXA_ETARIA", "DS_GRAU_ESCOLARIDADE"],
                        dropna=False,
                    )["QT_ELEITORES_PERFIL"]
                    .sum()
                    .reset_index()
                )
                for row in grouped.itertuples(index=False):
                    year = int(float(row.ANO_ELEICAO))
                    sex = _safe_dimension(row.DS_GENERO)
                    age = _safe_dimension(row.DS_FAIXA_ETARIA)
                    education = _safe_dimension(row.DS_GRAU_ESCOLARIDADE)
                    voters = int(row.QT_ELEITORES_PERFIL)
                    key = (year, sex, age, education)
                    aggregated[key] = aggregated.get(key, 0) + voters

    rows = [
        {
            "reference_year": year,
            "sex": sex,
            "age_range": age,
            "education": education,
            "voters": voters,
        }
        for (year, sex, age, education), voters in sorted(aggregated.items())
    ]

    info = {
        "csv_name": csv_name,
        "rows_scanned": rows_scanned,
        "rows_filtered": rows_filtered,
        "rows_aggregated": len(rows),
        "requested_year": requested_year,
    }
    return rows, info


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

        package_id = f"eleitorado-{reference_year}"
        package = _ckan_get_package(client, settings.tse_ckan_base_url, package_id)
        effective_package_id = package_id
        if package is None:
            package = _ckan_get_package(client, settings.tse_ckan_base_url, "eleitorado-atual")
            effective_package_id = "eleitorado-atual"
            warnings.append(
                (
                    f"CKAN package '{package_id}' not found; fallback to "
                    f"'{effective_package_id}'."
                )
            )
        if package is None:
            raise RuntimeError("Could not resolve electorate package from TSE CKAN.")

        resources = package.get("resources", [])
        if not isinstance(resources, list):
            raise RuntimeError("Invalid resources format in TSE CKAN package.")
        resource = _pick_electorate_resource(resources)
        if resource is None:
            raise RuntimeError("No electorate zip resource found in TSE CKAN package.")

        resource_url = str(resource.get("url", "")).strip()
        if not resource_url:
            raise RuntimeError("Selected TSE resource has empty URL.")

        zip_bytes, _ = client.download_bytes(
            resource_url,
            expected_content_types=["zip", "octet-stream", "application/octet-stream"],
            min_bytes=1024,
        )

        parsed_rows, parse_info = _extract_rows_from_zip(
            zip_bytes=zip_bytes,
            municipality_name=municipality_name,
            uf=uf,
            requested_year=reference_year,
        )
        if not parsed_rows:
            warnings.append(
                f"No electorate rows found for municipality '{municipality_name}' ({uf})."
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
        if parsed_rows:
            with session_scope(settings) as session:
                for row in parsed_rows:
                    session.execute(
                        text(
                            """
                            INSERT INTO silver.fact_electorate (
                                territory_id,
                                reference_year,
                                sex,
                                age_range,
                                education,
                                voters
                            )
                            VALUES (
                                CAST(:territory_id AS uuid),
                                :reference_year,
                                :sex,
                                :age_range,
                                :education,
                                :voters
                            )
                            ON CONFLICT (
                                territory_id,
                                reference_year,
                                sex,
                                age_range,
                                education
                            )
                            DO UPDATE SET
                                voters = EXCLUDED.voters
                            """
                        ),
                        {
                            "territory_id": territory_id,
                            "reference_year": row["reference_year"],
                            "sex": row["sex"],
                            "age_range": row["age_range"],
                            "education": row["education"],
                            "voters": row["voters"],
                        },
                    )
                    rows_written += 1

        checks = [
            {
                "name": "ckan_package_resolved",
                "status": "pass",
                "details": f"Package '{effective_package_id}' resolved.",
            },
            {
                "name": "electorate_rows_extracted",
                "status": "pass" if parsed_rows else "warn",
                "details": f"{len(parsed_rows)} electorate rows parsed for municipality.",
            },
            {
                "name": "electorate_rows_loaded",
                "status": "pass" if rows_written > 0 else "warn",
                "details": f"{rows_written} rows upserted into silver.fact_electorate.",
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
            notes="TSE electorate extraction and Silver upsert for municipality scope.",
            run_id=run_id,
            tables_written=["silver.fact_electorate"],
            rows_written=[{"table": "silver.fact_electorate", "rows": rows_written}],
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
            "TSE electorate job finished.",
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
            "TSE electorate job failed.",
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
