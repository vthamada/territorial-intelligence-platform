from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run

JOB_NAME = "dbt_build"
SOURCE = "INTERNAL"
DATASET_NAME = "gold_dbt_build"
WAVE = "MVP-1"
DBT_MODELS_DIR = Path("dbt_project/models/gold")


def _load_gold_models(models_dir: Path = DBT_MODELS_DIR) -> list[tuple[str, str]]:
    if not models_dir.exists():
        raise RuntimeError(f"dbt models directory not found: {models_dir}")

    models: list[tuple[str, str]] = []
    for path in sorted(models_dir.glob("*.sql")):
        model_name = path.stem.strip()
        sql = path.read_text(encoding="utf-8").strip()
        if not model_name or not sql:
            continue
        models.append((model_name, sql))

    if not models:
        raise RuntimeError(f"No SQL models found in {models_dir}")
    return models


def run(
    *,
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
    settings: Settings | None = None,
) -> dict[str, Any]:
    del force, max_retries, timeout_seconds
    settings = settings or get_settings()
    logger = get_logger(JOB_NAME)
    run_id = str(uuid4())
    started_at_utc = datetime.now(UTC)
    started_at = time.perf_counter()
    warnings: list[str] = []

    try:
        models = _load_gold_models()
        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": JOB_NAME,
                "status": "success",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": len(models),
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "preview": {
                    "models_dir": DBT_MODELS_DIR.as_posix(),
                    "models": [name for name, _ in models],
                    "build_mode": "sql_direct",
                },
            }

        built_models: list[dict[str, Any]] = []
        with session_scope(settings) as session:
            session.execute(text("CREATE SCHEMA IF NOT EXISTS gold"))
            for model_name, sql in models:
                session.execute(text(f"CREATE OR REPLACE VIEW gold.{model_name} AS\n{sql}"))
                row_count = session.execute(text(f"SELECT COUNT(*) FROM gold.{model_name}")).scalar_one()
                built_models.append({"model": model_name, "row_count": int(row_count)})

        rows_written = len(built_models)
        bronze_payload = {
            "job": JOB_NAME,
            "reference_period": reference_period,
            "build_mode": "sql_direct",
            "models_dir": DBT_MODELS_DIR.as_posix(),
            "built_models": built_models,
        }
        raw_bytes = json.dumps(bronze_payload, ensure_ascii=False).encode("utf-8")
        checks = [
            {
                "name": "gold_models_discovered",
                "status": "pass" if models else "fail",
                "details": f"{len(models)} SQL model(s) discovered.",
            },
            {
                "name": "gold_models_built",
                "status": "pass" if rows_written > 0 else "fail",
                "details": f"{rows_written} model(s) built in gold schema.",
            },
        ]
        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=reference_period,
            raw_bytes=raw_bytes,
            extension=".json",
            uri=f"dbt://{DBT_MODELS_DIR.as_posix()}",
            territory_scope="municipality",
            dataset_version="sql-direct-v1",
            checks=checks,
            notes="Gold layer build from dbt_project/models/gold SQL models.",
            run_id=run_id,
            tables_written=[f"gold.{item['model']}" for item in built_models],
            rows_written=[{"table": f"gold.{item['model']}", "rows": item["row_count"]} for item in built_models],
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
                rows_extracted=len(models),
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "build_mode": "sql_direct",
                    "models": built_models,
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
            "dbt_build finished.",
            run_id=run_id,
            rows_extracted=len(models),
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "success",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": len(models),
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
            "dbt_build failed.",
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
