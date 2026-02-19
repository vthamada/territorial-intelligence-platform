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

_ELECTORATE_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "ANO_ELEICAO": ("ANO_ELEICAO",),
    "NR_ZONA": ("NR_ZONA",),
    "SG_UF": ("SG_UF",),
    "NM_MUNICIPIO": ("NM_MUNICIPIO",),
    "DS_GENERO": ("DS_GENERO",),
    "DS_FAIXA_ETARIA": ("DS_FAIXA_ETARIA",),
    "DS_GRAU_ESCOLARIDADE": ("DS_GRAU_ESCOLARIDADE", "DS_GRAU_INSTRUCAO"),
    "QT_ELEITORES_PERFIL": ("QT_ELEITORES_PERFIL", "QT_ELEITORES"),
}


def _normalize_text(value: str) -> str:
    stripped = value.strip().casefold()
    return "".join(ch for ch in unicodedata.normalize("NFKD", stripped) if not unicodedata.combining(ch))


def _safe_dimension(value: Any) -> str:
    raw = "" if value is None else str(value).strip()
    return raw if raw else "NAO_INFORMADO"


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


def _resolve_electorate_package(
    client: HttpClient,
    base_url: str,
    reference_year: int,
) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    warnings: list[str] = []
    candidate_ids = [
        f"eleitorado-{reference_year}",
        "eleitorado-2024",
        "eleitorado-2022",
        "eleitorado-2020",
        "eleitorado-2018",
        "eleitorado-2016",
        "eleitorado-atual",
    ]
    ordered_candidates = list(dict.fromkeys(candidate_ids))
    requested_id = f"eleitorado-{reference_year}"
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


def _resolve_electorate_columns(columns: list[str]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for canonical, aliases in _ELECTORATE_COLUMN_ALIASES.items():
        if canonical == "NR_ZONA":
            selected_optional = next((alias for alias in aliases if alias in columns), None)
            if selected_optional is not None:
                resolved[canonical] = selected_optional
            continue
        selected = next((alias for alias in aliases if alias in columns), None)
        if selected is None:
            aliases_display = ", ".join(aliases)
            raise ValueError(
                f"Required electorate column '{canonical}' not found. "
                f"Accepted aliases: {aliases_display}."
            )
        resolved[canonical] = selected
    return resolved


def _extract_rows_from_zip(
    *,
    zip_bytes: bytes,
    municipality_name: str,
    uf: str,
    requested_year: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    target_name = _normalize_text(municipality_name)
    aggregated_municipality: dict[tuple[int, str, str, str], int] = {}
    aggregated_zone: dict[tuple[int, str, str, str, str], int] = {}
    csv_name = ""
    rows_scanned = 0
    rows_filtered = 0
    column_mapping: dict[str, str] = {}

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        csv_files = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_files:
            raise ValueError("Zip payload has no CSV file.")
        csv_name = csv_files[0]

        with archive.open(csv_name) as csv_bytes:
            wrapper = io.TextIOWrapper(csv_bytes, encoding="latin1", newline="")
            header_df = pd.read_csv(wrapper, sep=";", nrows=0, low_memory=False)
            column_mapping = _resolve_electorate_columns(list(header_df.columns))

        with archive.open(csv_name) as csv_bytes:
            wrapper = io.TextIOWrapper(csv_bytes, encoding="latin1", newline="")
            chunks = pd.read_csv(
                wrapper,
                sep=";",
                usecols=list(column_mapping.values()),
                chunksize=200_000,
                low_memory=False,
            )
            for chunk in chunks:
                chunk = chunk.rename(columns={actual: canonical for canonical, actual in column_mapping.items()})
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
                    aggregated_municipality[key] = aggregated_municipality.get(key, 0) + voters

                if "NR_ZONA" in filtered.columns:
                    filtered["NR_ZONA"] = filtered["NR_ZONA"].map(_normalize_zone_code)
                    grouped_zone = (
                        filtered[filtered["NR_ZONA"].notna()]
                        .groupby(
                            [
                                "ANO_ELEICAO",
                                "NR_ZONA",
                                "DS_GENERO",
                                "DS_FAIXA_ETARIA",
                                "DS_GRAU_ESCOLARIDADE",
                            ],
                            dropna=False,
                        )["QT_ELEITORES_PERFIL"]
                        .sum()
                        .reset_index()
                    )
                    for row in grouped_zone.itertuples(index=False):
                        zone_code = _normalize_zone_code(row.NR_ZONA)
                        if zone_code is None:
                            continue
                        year = int(float(row.ANO_ELEICAO))
                        sex = _safe_dimension(row.DS_GENERO)
                        age = _safe_dimension(row.DS_FAIXA_ETARIA)
                        education = _safe_dimension(row.DS_GRAU_ESCOLARIDADE)
                        voters = int(row.QT_ELEITORES_PERFIL)
                        key_zone = (year, zone_code, sex, age, education)
                        aggregated_zone[key_zone] = aggregated_zone.get(key_zone, 0) + voters

    municipality_rows = [
        {
            "reference_year": year,
            "sex": sex,
            "age_range": age,
            "education": education,
            "voters": voters,
        }
        for (year, sex, age, education), voters in sorted(aggregated_municipality.items())
    ]
    zone_rows = [
        {
            "reference_year": year,
            "tse_zone": zone_code,
            "sex": sex,
            "age_range": age,
            "education": education,
            "voters": voters,
        }
        for (year, zone_code, sex, age, education), voters in sorted(aggregated_zone.items())
    ]

    info = {
        "csv_name": csv_name,
        "rows_scanned": rows_scanned,
        "rows_filtered": rows_filtered,
        "rows_aggregated_municipality": len(municipality_rows),
        "rows_aggregated_zone": len(zone_rows),
        "has_zone_column": "NR_ZONA" in column_mapping,
        "requested_year": requested_year,
        "column_mapping": column_mapping,
    }
    return municipality_rows, zone_rows, info


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

        package, effective_package_id, package_warnings = _resolve_electorate_package(
            client,
            settings.tse_ckan_base_url,
            reference_year,
        )
        warnings.extend(package_warnings)
        if package is None:
            raise RuntimeError("Could not resolve electorate package from TSE CKAN.")
        if effective_package_id is None:
            raise RuntimeError("Could not determine electorate package identifier.")

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

        parsed_rows_municipality, parsed_rows_zone, parse_info = _extract_rows_from_zip(
            zip_bytes=zip_bytes,
            municipality_name=municipality_name,
            uf=uf,
            requested_year=reference_year,
        )
        extracted_years = sorted(
            {
                int(item["reference_year"])
                for item in (*parsed_rows_municipality, *parsed_rows_zone)
                if item.get("reference_year") is not None
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
                f"No electorate rows found for municipality '{municipality_name}' ({uf})."
            )
        if not parse_info.get("has_zone_column", False):
            warnings.append(
                "Electorate dataset has no zone column (NR_ZONA); zone-level electorate rows were not generated."
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
        municipality_rows_written = 0
        zone_rows_written = 0
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
                    municipality_rows_written += 1

                for row in parsed_rows_zone:
                    zone_id = zone_territory_ids.get(str(row["tse_zone"]))
                    if zone_id is None:
                        warnings.append(
                            f"Skipped electorate row because zone territory could not be resolved: {row['tse_zone']}."
                        )
                        continue
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
                            "territory_id": zone_id,
                            "reference_year": row["reference_year"],
                            "sex": row["sex"],
                            "age_range": row["age_range"],
                            "education": row["education"],
                            "voters": row["voters"],
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
                "name": "electorate_rows_extracted",
                "status": "pass" if parsed_rows_municipality or parsed_rows_zone else "warn",
                "details": (
                    f"{len(parsed_rows_municipality)} municipality rows and "
                    f"{len(parsed_rows_zone)} zone rows parsed."
                ),
            },
            {
                "name": "electorate_rows_loaded",
                "status": "pass" if rows_written > 0 else "warn",
                "details": f"{rows_written} rows upserted into silver.fact_electorate.",
            },
            {
                "name": "electorate_zone_rows_loaded",
                "status": "pass" if zone_rows_written > 0 else "warn",
                "details": f"{zone_rows_written} zone rows upserted into silver.fact_electorate.",
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
            tables_written=["silver.fact_electorate", "silver.dim_territory"],
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
            "TSE electorate job finished.",
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
