from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run

JOB_NAME = "ibge_admin_fetch"
DATASET_NAME = "ibge_localidades_distritos"
SOURCE = "IBGE"


def _parse_districts(payload: Any, municipality_code: str) -> list[dict[str, str]]:
    if not isinstance(payload, list):
        raise ValueError("IBGE districts payload must be a list.")

    results: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        municipality = item.get("municipio", {}) if isinstance(item.get("municipio"), dict) else {}
        municipio_id = str(municipality.get("id", ""))
        if municipio_id and municipio_id != municipality_code:
            continue

        district_id = str(item.get("id", "")).strip()
        district_name = str(item.get("nome", "")).strip()
        if not district_id or not district_name:
            continue
        results.append({"district_id": district_id, "district_name": district_name})
    return results


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
        endpoint = (
            f"{settings.ibge_api_base_url}/municipios/{settings.municipality_ibge_code}/distritos"
        )
        payload = client.get_json(endpoint)
        raw_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        districts = _parse_districts(payload, settings.municipality_ibge_code)
        if not districts:
            warnings.append("No districts returned from IBGE API.")

        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": JOB_NAME,
                "status": "success",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": len(districts),
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "bronze_preview": {
                    "source": SOURCE,
                    "dataset": DATASET_NAME,
                    "reference_period": reference_period,
                    "uri": endpoint,
                    "size_bytes": len(raw_bytes),
                },
            }

        with session_scope(settings) as session:
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
                        municipality_ibge_code
                    )
                    VALUES (
                        'municipality',
                        NULL,
                        :canonical_key,
                        :source_system,
                        :source_entity_id,
                        :ibge_geocode,
                        '',
                        '',
                        :name,
                        :normalized_name,
                        :uf,
                        :municipality_ibge_code
                    )
                    ON CONFLICT (level, ibge_geocode, tse_zone, tse_section, municipality_ibge_code)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        normalized_name = EXCLUDED.normalized_name,
                        uf = EXCLUDED.uf,
                        updated_at = NOW()
                    """
                ),
                {
                    "canonical_key": f"municipality:ibge:{settings.municipality_ibge_code}",
                    "source_system": "IBGE",
                    "source_entity_id": settings.municipality_ibge_code,
                    "ibge_geocode": settings.municipality_ibge_code,
                    "name": "Diamantina",
                    "normalized_name": "diamantina",
                    "uf": "MG",
                    "municipality_ibge_code": settings.municipality_ibge_code,
                },
            )

            municipality_row = session.execute(
                text(
                    """
                    SELECT territory_id
                    FROM silver.dim_territory
                    WHERE level = 'municipality'
                      AND ibge_geocode = :code
                      AND municipality_ibge_code = :code
                    ORDER BY territory_id
                    LIMIT 1
                    """
                ),
                {"code": settings.municipality_ibge_code},
            ).first()
            if municipality_row is None:
                raise RuntimeError("Failed to resolve municipality territory_id in dim_territory.")
            municipality_id = municipality_row[0]

            for district in districts:
                normalized_name = district["district_name"].strip().lower()
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
                            municipality_ibge_code
                        )
                        VALUES (
                            'district',
                            :parent_territory_id,
                            :canonical_key,
                            :source_system,
                            :source_entity_id,
                            :ibge_geocode,
                            '',
                            '',
                            :name,
                            :normalized_name,
                            :uf,
                            :municipality_ibge_code
                        )
                        ON CONFLICT (level, ibge_geocode, tse_zone, tse_section, municipality_ibge_code)
                        DO UPDATE SET
                            parent_territory_id = EXCLUDED.parent_territory_id,
                            name = EXCLUDED.name,
                            normalized_name = EXCLUDED.normalized_name,
                            uf = EXCLUDED.uf,
                            updated_at = NOW()
                        """
                    ),
                    {
                        "parent_territory_id": municipality_id,
                        "canonical_key": f"district:ibge:{district['district_id']}",
                        "source_system": "IBGE",
                        "source_entity_id": district["district_id"],
                        "ibge_geocode": district["district_id"],
                        "name": district["district_name"],
                        "normalized_name": normalized_name,
                        "uf": "MG",
                        "municipality_ibge_code": settings.municipality_ibge_code,
                    },
                )

        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=reference_period,
            raw_bytes=raw_bytes,
            extension=".json",
            uri=endpoint,
            territory_scope="district",
            dataset_version="api-v1",
        checks=[
            {
                "name": "municipality_match",
                "status": "pass",
                "details": f"Municipality scope {settings.municipality_ibge_code}",
                },
                {
                    "name": "district_count",
                    "status": "warn" if not districts else "pass",
                    "details": f"{len(districts)} districts parsed.",
                },
            ],
            notes="Municipality + district upsert in dim_territory.",
            run_id=run_id,
            tables_written=["silver.dim_territory"],
            rows_written=[{"table": "silver.dim_territory", "rows": len(districts) + 1}],
        )

        finished_at_utc = datetime.now(UTC)
        with session_scope(settings) as session:
            upsert_pipeline_run(
                session=session,
                run_id=run_id,
                job_name=JOB_NAME,
                source=SOURCE,
                dataset=DATASET_NAME,
                wave="MVP-1",
                reference_period=reference_period,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
                status="success",
                rows_extracted=len(districts),
                rows_loaded=len(districts) + 1,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={"district_count": len(districts)},
            )
            replace_pipeline_checks_from_dicts(
                session=session,
                run_id=run_id,
                checks=[
                    {
                        "name": "municipality_match",
                        "status": "pass",
                        "details": f"Municipality scope {settings.municipality_ibge_code}",
                        "observed_value": 1,
                        "threshold_value": 1,
                    },
                    {
                        "name": "district_count",
                        "status": "warn" if not districts else "pass",
                        "details": f"{len(districts)} districts parsed.",
                        "observed_value": len(districts),
                        "threshold_value": 1,
                    },
                ],
            )

        elapsed = time.perf_counter() - started_at
        logger.info(
            "IBGE admin job finished.",
            run_id=run_id,
            rows_extracted=len(districts),
            rows_written=len(districts) + 1,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "success",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": len(districts),
            "rows_written": len(districts) + 1,
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
                        wave="MVP-1",
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
            "IBGE admin job failed.",
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
