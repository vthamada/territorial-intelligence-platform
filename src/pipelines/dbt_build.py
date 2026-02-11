from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
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
DBT_PROJECT_DIR = Path("dbt_project")
DBT_MODELS_DIR = Path("dbt_project/models/gold")
ALLOWED_BUILD_MODES = ("auto", "dbt", "sql_direct")


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


def _resolve_requested_build_mode() -> str:
    requested_mode = os.getenv("DBT_BUILD_MODE", "auto").strip().lower()
    if requested_mode not in ALLOWED_BUILD_MODES:
        allowed = ", ".join(ALLOWED_BUILD_MODES)
        raise RuntimeError(f"Invalid DBT_BUILD_MODE={requested_mode!r}. Allowed values: {allowed}.")
    return requested_mode


def _dbt_cli_available() -> bool:
    return _resolve_dbt_executable() is not None


def _resolve_dbt_executable() -> str | None:
    on_path = shutil.which("dbt")
    if on_path:
        return on_path

    scripts_dir = Path(sys.executable).resolve().parent
    candidates = [scripts_dir / "dbt", scripts_dir / "dbt.exe"]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _decide_effective_build_mode(requested_mode: str, dbt_available: bool) -> str:
    if requested_mode == "dbt":
        if not dbt_available:
            raise RuntimeError("DBT_BUILD_MODE='dbt' but dbt CLI is not available in PATH.")
        return "dbt_cli"
    if requested_mode == "auto" and dbt_available:
        return "dbt_cli"
    return "sql_direct"


def _build_dbt_base_command() -> list[str]:
    executable = _resolve_dbt_executable() or "dbt"
    command = [executable, "run", "--project-dir", DBT_PROJECT_DIR.as_posix()]

    profiles_dir = os.getenv("DBT_PROFILES_DIR", "").strip()
    if profiles_dir:
        command.extend(["--profiles-dir", profiles_dir])

    profile_name = os.getenv("DBT_PROFILE", "").strip()
    if profile_name:
        command.extend(["--profile", profile_name])

    target_name = os.getenv("DBT_TARGET", "").strip()
    if target_name:
        command.extend(["--target", target_name])

    return command


def _build_dbt_run_command(reference_period: str) -> list[str]:
    command = _build_dbt_base_command()
    vars_payload = json.dumps({"reference_period": reference_period}, ensure_ascii=False)
    command.extend(["--vars", vars_payload])
    return command


def _tail(text: str, max_chars: int = 2000) -> str:
    clean = text.strip()
    if len(clean) <= max_chars:
        return clean
    return clean[-max_chars:]


def _run_dbt_cli(reference_period: str, timeout_seconds: int) -> dict[str, str]:
    command = _build_dbt_run_command(reference_period)
    try:
        result = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=max(1, timeout_seconds),
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"dbt CLI timed out after {timeout_seconds} second(s).") from exc

    if result.returncode != 0:
        stderr_tail = _tail(result.stderr)
        stdout_tail = _tail(result.stdout)
        raise RuntimeError(
            f"dbt CLI failed with exit code {result.returncode}. "
            f"stdout_tail={stdout_tail!r} stderr_tail={stderr_tail!r}"
        )

    return {
        "command": " ".join(command),
        "stdout_tail": _tail(result.stdout),
        "stderr_tail": _tail(result.stderr),
    }


def _run_sql_direct_build(
    *,
    settings: Settings,
    models: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    built_models: list[dict[str, Any]] = []
    with session_scope(settings) as session:
        session.execute(text("CREATE SCHEMA IF NOT EXISTS gold"))
        for model_name, sql in models:
            session.execute(text(f"CREATE OR REPLACE VIEW gold.{model_name} AS\n{sql}"))
            row_count = session.execute(
                text(f"SELECT COUNT(*) FROM gold.{model_name}")
            ).scalar_one()
            built_models.append({"model": model_name, "row_count": int(row_count)})
    return built_models


def _collect_gold_model_row_counts(
    *,
    settings: Settings,
    model_names: list[str],
) -> list[dict[str, Any]]:
    built_models: list[dict[str, Any]] = []
    with session_scope(settings) as session:
        for model_name in model_names:
            row_count = session.execute(
                text(f"SELECT COUNT(*) FROM gold.{model_name}")
            ).scalar_one()
            built_models.append({"model": model_name, "row_count": int(row_count)})
    return built_models


def run(
    *,
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
    settings: Settings | None = None,
) -> dict[str, Any]:
    del force, max_retries
    settings = settings or get_settings()
    logger = get_logger(JOB_NAME)
    run_id = str(uuid4())
    started_at_utc = datetime.now(UTC)
    started_at = time.perf_counter()
    warnings: list[str] = []

    try:
        models = _load_gold_models()
        requested_mode = _resolve_requested_build_mode()
        dbt_available = _dbt_cli_available()
        effective_mode = _decide_effective_build_mode(requested_mode, dbt_available)

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
                    "build_mode_requested": requested_mode,
                    "build_mode_effective": effective_mode,
                },
            }

        dbt_cli_meta: dict[str, str] | None = None
        model_names = [name for name, _ in models]
        if effective_mode == "dbt_cli":
            try:
                dbt_cli_meta = _run_dbt_cli(reference_period, timeout_seconds)
                built_models = _collect_gold_model_row_counts(
                    settings=settings,
                    model_names=model_names,
                )
            except Exception as exc:
                if requested_mode != "auto":
                    raise
                warnings.append(
                    "dbt CLI execution failed in auto mode; falling back to sql_direct. "
                    f"Cause: {exc}"
                )
                effective_mode = "sql_direct"
                built_models = _run_sql_direct_build(settings=settings, models=models)
        else:
            built_models = _run_sql_direct_build(settings=settings, models=models)

        rows_written = len(built_models)
        bronze_payload = {
            "job": JOB_NAME,
            "reference_period": reference_period,
            "build_mode_requested": requested_mode,
            "build_mode_effective": effective_mode,
            "models_dir": DBT_MODELS_DIR.as_posix(),
            "built_models": built_models,
            "dbt_cli": dbt_cli_meta,
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
            {
                "name": "gold_build_mode",
                "status": "pass",
                "details": f"Build mode effective: {effective_mode}.",
            },
        ]
        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=reference_period,
            raw_bytes=raw_bytes,
            extension=".json",
            uri=f"dbt://{DBT_PROJECT_DIR.as_posix()}",
            territory_scope="municipality",
            dataset_version=f"{effective_mode}-v1",
            checks=checks,
            notes=(
                "Gold layer build from dbt project. "
                "Uses dbt CLI when available/configured, with sql_direct fallback in auto mode."
            ),
            run_id=run_id,
            tables_written=[f"gold.{item['model']}" for item in built_models],
            rows_written=[
                {"table": f"gold.{item['model']}", "rows": item["row_count"]}
                for item in built_models
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
                rows_extracted=len(models),
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "build_mode_requested": requested_mode,
                    "build_mode_effective": effective_mode,
                    "models": built_models,
                    "dbt_cli": dbt_cli_meta,
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
            build_mode=effective_mode,
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
            "build_mode": effective_mode,
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
                    replace_pipeline_checks_from_dicts(
                        session=session,
                        run_id=run_id,
                        checks=[
                            {
                                "name": "dbt_build_execution",
                                "status": "fail",
                                "details": f"dbt_build failed: {exc}",
                            }
                        ],
                    )
            except Exception:
                logger.exception(
                    "Could not persist failed pipeline run in ops tables.",
                    run_id=run_id,
                )

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
