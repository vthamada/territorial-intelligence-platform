from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import sqlalchemy as sa
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    src_str = str(SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

from app.settings import get_settings  # noqa: E402
from pipelines.ana_hydrology import run as run_ana_hydrology  # noqa: E402
from pipelines.anatel_connectivity import run as run_anatel_connectivity  # noqa: E402
from pipelines.aneel_energy import run as run_aneel_energy  # noqa: E402
from pipelines.cneas_social_assistance import run as run_cneas_social_assistance  # noqa: E402
from pipelines.cecad_social_protection import run as run_cecad_social_protection  # noqa: E402
from pipelines.censo_suas import run as run_censo_suas  # noqa: E402
from pipelines.datasus_health import run as run_datasus_health  # noqa: E402
from pipelines.dbt_build import run as run_dbt_build  # noqa: E402
from pipelines.ibge_admin import run as run_ibge_admin  # noqa: E402
from pipelines.ibge_geometries import run as run_ibge_geometries  # noqa: E402
from pipelines.ibge_indicators import run as run_ibge_indicators  # noqa: E402
from pipelines.inep_education import run as run_inep_education  # noqa: E402
from pipelines.inmet_climate import run as run_inmet_climate  # noqa: E402
from pipelines.inpe_queimadas import run as run_inpe_queimadas  # noqa: E402
from pipelines.mte_labor import run as run_mte_labor  # noqa: E402
from pipelines.quality_suite import run as run_quality_suite  # noqa: E402
from pipelines.sejusp_public_safety import run as run_sejusp_public_safety  # noqa: E402
from pipelines.senatran_fleet import run as run_senatran_fleet  # noqa: E402
from pipelines.siconfi_finance import run as run_siconfi_finance  # noqa: E402
from pipelines.portal_transparencia import run as run_portal_transparencia  # noqa: E402
from pipelines.sidra_indicators import run as run_sidra_indicators  # noqa: E402
from pipelines.siops_health_finance import run as run_siops_health_finance  # noqa: E402
from pipelines.snis_sanitation import run as run_snis_sanitation  # noqa: E402
from pipelines.tse_catalog import run as run_tse_catalog  # noqa: E402
from pipelines.tse_electorate import run as run_tse_electorate  # noqa: E402
from pipelines.tse_results import run as run_tse_results  # noqa: E402
from pipelines.urban_pois import run as run_urban_pois  # noqa: E402
from pipelines.urban_roads import run as run_urban_roads  # noqa: E402
from pipelines.urban_transport import run as run_urban_transport  # noqa: E402
from pipelines.suasweb_social_assistance import run as run_suasweb_social_assistance  # noqa: E402

Runner = Callable[..., dict[str, Any]]

JOB_RUNNERS: dict[str, Runner] = {
    "ibge_admin_fetch": run_ibge_admin,
    "ibge_geometries_fetch": run_ibge_geometries,
    "ibge_indicators_fetch": run_ibge_indicators,
    "tse_catalog_discovery": run_tse_catalog,
    "tse_electorate_fetch": run_tse_electorate,
    "tse_results_fetch": run_tse_results,
    "education_inep_fetch": run_inep_education,
    "health_datasus_fetch": run_datasus_health,
    "finance_siconfi_fetch": run_siconfi_finance,
    "portal_transparencia_fetch": run_portal_transparencia,
    "labor_mte_fetch": run_mte_labor,
    "sidra_indicators_fetch": run_sidra_indicators,
    "senatran_fleet_fetch": run_senatran_fleet,
    "sejusp_public_safety_fetch": run_sejusp_public_safety,
    "siops_health_finance_fetch": run_siops_health_finance,
    "snis_sanitation_fetch": run_snis_sanitation,
    "inmet_climate_fetch": run_inmet_climate,
    "inpe_queimadas_fetch": run_inpe_queimadas,
    "ana_hydrology_fetch": run_ana_hydrology,
    "anatel_connectivity_fetch": run_anatel_connectivity,
    "aneel_energy_fetch": run_aneel_energy,
    "suasweb_social_assistance_fetch": run_suasweb_social_assistance,
    "cneas_social_assistance_fetch": run_cneas_social_assistance,
    "cecad_social_protection_fetch": run_cecad_social_protection,
    "censo_suas_fetch": run_censo_suas,
    "urban_roads_fetch": run_urban_roads,
    "urban_pois_fetch": run_urban_pois,
    "urban_transport_fetch": run_urban_transport,
}

POST_LOAD_RUNNERS: dict[str, Runner] = {
    "dbt_build": run_dbt_build,
    "quality_suite": run_quality_suite,
}

JOB_ORDER: tuple[str, ...] = (
    "ibge_admin_fetch",
    "ibge_geometries_fetch",
    "ibge_indicators_fetch",
    "tse_catalog_discovery",
    "tse_electorate_fetch",
    "tse_results_fetch",
    "education_inep_fetch",
    "health_datasus_fetch",
    "finance_siconfi_fetch",
    "labor_mte_fetch",
    "sidra_indicators_fetch",
    "senatran_fleet_fetch",
    "sejusp_public_safety_fetch",
    "siops_health_finance_fetch",
    "snis_sanitation_fetch",
    "inmet_climate_fetch",
    "inpe_queimadas_fetch",
    "ana_hydrology_fetch",
    "anatel_connectivity_fetch",
    "aneel_energy_fetch",
    "suasweb_social_assistance_fetch",
    "cneas_social_assistance_fetch",
    "cecad_social_protection_fetch",
    "censo_suas_fetch",
    "urban_roads_fetch",
    "urban_pois_fetch",
    "urban_transport_fetch",
    "portal_transparencia_fetch",
)

GOVERNED_CONNECTORS: frozenset[str] = frozenset(
    {
        "cecad_social_protection_fetch",
        "censo_suas_fetch",
    }
)


def _parse_csv_values(raw: str) -> list[str]:
    values = [item.strip() for item in str(raw).split(",")]
    return [item for item in values if item]


def _load_job_default_periods(config_path: Path) -> dict[str, str]:
    if not config_path.exists():
        return {}
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    jobs = payload.get("jobs") if isinstance(payload, dict) else {}
    if not isinstance(jobs, dict):
        return {}
    defaults: dict[str, str] = {}
    for job_name, metadata in jobs.items():
        if not isinstance(metadata, dict):
            continue
        period = metadata.get("reference_period")
        if period is None:
            continue
        token = str(period).strip()
        if token:
            defaults[str(job_name)] = token
    return defaults


def _load_incremental_candidates(database_url: str, *, include_partial: bool) -> list[str]:
    statuses = ["implemented", "partial"] if include_partial else ["implemented"]
    statement = (
        sa.text(
            """
            SELECT connector_name
            FROM ops.connector_registry
            WHERE source <> 'INTERNAL'
              AND status::text IN :statuses
            ORDER BY connector_name
            """
        )
        .bindparams(sa.bindparam("statuses", expanding=True))
    )
    engine = sa.create_engine(database_url)
    with engine.begin() as conn:
        rows = conn.execute(statement, {"statuses": statuses}).fetchall()
    return [str(row[0]) for row in rows]


def _fetch_latest_runs(
    database_url: str,
    *,
    jobs: list[str],
    periods: list[str],
) -> dict[tuple[str, str], dict[str, Any]]:
    if not jobs or not periods:
        return {}
    statement = (
        sa.text(
            """
            SELECT
                job_name,
                COALESCE(reference_period, '') AS reference_period,
                status,
                started_at_utc
            FROM ops.pipeline_runs
            WHERE job_name IN :job_names
              AND COALESCE(reference_period, '') IN :periods
            ORDER BY started_at_utc DESC
            """
        )
        .bindparams(
            sa.bindparam("job_names", expanding=True),
            sa.bindparam("periods", expanding=True),
        )
    )
    engine = sa.create_engine(database_url)
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    with engine.begin() as conn:
        rows = conn.execute(statement, {"job_names": jobs, "periods": periods}).mappings().all()
    for row in rows:
        key = (str(row["job_name"]), str(row["reference_period"]))
        if key in latest:
            continue
        latest[key] = {
            "latest_status": str(row["status"]),
            "latest_started_at_utc": row["started_at_utc"],
        }
    return latest


def _job_order(job_name: str) -> int:
    try:
        return JOB_ORDER.index(job_name)
    except ValueError:
        return len(JOB_ORDER) + 100


def _decide_incremental_action(
    *,
    job_name: str,
    reference_period: str,
    latest_status: str | None,
    latest_started_at_utc: datetime | None,
    now_utc: datetime,
    stale_after_hours: int,
    reprocess_jobs: set[str],
    reprocess_periods: set[str],
) -> dict[str, Any]:
    if job_name in reprocess_jobs or reference_period in reprocess_periods:
        return {"execute": True, "reason": "reprocess_selected", "age_hours": None}

    if latest_status is None:
        return {"execute": True, "reason": "no_previous_run", "age_hours": None}

    if latest_status != "success":
        return {
            "execute": True,
            "reason": f"latest_status_{latest_status}",
            "age_hours": None,
        }

    if latest_started_at_utc is None:
        return {"execute": True, "reason": "success_without_timestamp", "age_hours": None}

    age_hours = max(0.0, (now_utc - latest_started_at_utc).total_seconds() / 3600.0)
    if age_hours >= float(stale_after_hours):
        return {
            "execute": True,
            "reason": f"stale_success_ge_{stale_after_hours}h",
            "age_hours": round(age_hours, 2),
        }

    return {
        "execute": False,
        "reason": f"fresh_success_lt_{stale_after_hours}h",
        "age_hours": round(age_hours, 2),
    }


def _run_job(
    *,
    label: str,
    fn: Runner,
    reference_period: str,
    force: bool,
    dry_run: bool,
    timeout_seconds: int,
    max_retries: int,
    phase: str,
) -> dict[str, Any]:
    started_at_utc = datetime.now(tz=UTC)
    try:
        result = fn(
            reference_period=reference_period,
            force=force,
            dry_run=dry_run,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        status = str(result.get("status", "unknown"))
        rows_loaded = int(result.get("rows_written", result.get("rows_loaded", 0)) or 0)
        error: str | None = None
    except Exception as exc:  # pragma: no cover - defensive guard for runtime orchestration
        result = {"status": "failed", "error": str(exc)}
        status = "failed"
        rows_loaded = 0
        error = str(exc)

    finished_at_utc = datetime.now(tz=UTC)
    return {
        "job": label,
        "phase": phase,
        "reference_period": reference_period,
        "status": status,
        "rows_loaded": rows_loaded,
        "started_at_utc": started_at_utc.isoformat(),
        "finished_at_utc": finished_at_utc.isoformat(),
        "error": error,
        "result": result,
    }


def _summarize_status(rows: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in rows:
        key = str(item.get("status", "unknown"))
        summary[key] = summary.get(key, 0) + 1
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run BD-080 incremental loads with selective reprocessing using "
            "ops.pipeline_runs as execution history."
        )
    )
    parser.add_argument("--periods", default="")
    parser.add_argument("--jobs", default="")
    parser.add_argument("--exclude-jobs", default="")
    parser.add_argument("--reprocess-jobs", default="")
    parser.add_argument("--reprocess-periods", default="")
    parser.add_argument("--include-partial", action="store_true")
    parser.add_argument("--skip-dbt", action="store_true")
    parser.add_argument("--skip-quality", action="store_true")
    parser.add_argument("--stale-after-hours", type=int, default=168)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-blocked", action="store_true")
    parser.add_argument(
        "--allow-governed-sources",
        action="store_true",
        help=(
            "Include connectors that require governed authentication/authorization "
            "(e.g., CECAD/Censo SUAS). By default they are skipped to keep "
            "execution focused on open-access sources."
        ),
    )
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument(
        "--output-json",
        default="data/reports/incremental_backfill_report.json",
    )
    args = parser.parse_args(argv)

    if args.stale_after_hours < 1:
        raise RuntimeError("--stale-after-hours must be >= 1")

    settings = get_settings()
    now_utc = datetime.now(tz=UTC)
    default_periods = _load_job_default_periods(PROJECT_ROOT / "configs" / "jobs.yml")

    registered_jobs = _load_incremental_candidates(
        settings.database_url,
        include_partial=bool(args.include_partial),
    )
    selected_jobs = registered_jobs

    requested_jobs = _parse_csv_values(args.jobs)
    if requested_jobs:
        selected_jobs = [job for job in selected_jobs if job in requested_jobs]
        unknown_requested = sorted(set(requested_jobs) - set(JOB_RUNNERS))
        if unknown_requested:
            raise RuntimeError(
                "Unknown jobs in --jobs: " + ", ".join(unknown_requested)
            )

    excluded_jobs = set(_parse_csv_values(args.exclude_jobs))
    selected_jobs = [job for job in selected_jobs if job not in excluded_jobs]

    if not args.allow_governed_sources:
        selected_jobs = [job for job in selected_jobs if job not in GOVERNED_CONNECTORS]

    selected_jobs = [job for job in selected_jobs if job in JOB_RUNNERS]
    if not selected_jobs:
        raise RuntimeError("No incremental jobs selected after filters.")

    period_override = _parse_csv_values(args.periods)
    reprocess_jobs = set(_parse_csv_values(args.reprocess_jobs))
    reprocess_periods = set(_parse_csv_values(args.reprocess_periods))

    job_period_pairs: list[tuple[str, str]] = []
    for job_name in sorted(selected_jobs, key=_job_order):
        periods = period_override or [default_periods.get(job_name, str(now_utc.year))]
        for period in periods:
            job_period_pairs.append((job_name, period))

    history = _fetch_latest_runs(
        settings.database_url,
        jobs=sorted({item[0] for item in job_period_pairs}),
        periods=sorted({item[1] for item in job_period_pairs}),
    )

    plan: list[dict[str, Any]] = []
    for job_name, period in job_period_pairs:
        state = history.get((job_name, period), {})
        decision = _decide_incremental_action(
            job_name=job_name,
            reference_period=period,
            latest_status=state.get("latest_status"),
            latest_started_at_utc=state.get("latest_started_at_utc"),
            now_utc=now_utc,
            stale_after_hours=args.stale_after_hours,
            reprocess_jobs=reprocess_jobs,
            reprocess_periods=reprocess_periods,
        )
        latest_started_at = state.get("latest_started_at_utc")
        plan.append(
            {
                "job": job_name,
                "reference_period": period,
                "execute": bool(decision["execute"]),
                "reason": str(decision["reason"]),
                "age_hours": decision["age_hours"],
                "latest_status": state.get("latest_status"),
                "latest_started_at_utc": (
                    latest_started_at.isoformat() if latest_started_at is not None else None
                ),
            }
        )

    executions: list[dict[str, Any]] = []
    period_successes: dict[str, bool] = {}
    for item in plan:
        if not item["execute"]:
            continue
        job_name = str(item["job"])
        period = str(item["reference_period"])
        run_result = _run_job(
            label=job_name,
            fn=JOB_RUNNERS[job_name],
            reference_period=period,
            force=bool(args.force),
            dry_run=bool(args.dry_run),
            timeout_seconds=int(args.timeout_seconds),
            max_retries=int(args.max_retries),
            phase="incremental",
        )
        executions.append(run_result)
        if run_result["status"] == "success":
            period_successes[period] = True
        else:
            period_successes.setdefault(period, False)

    post_runs: list[dict[str, Any]] = []
    success_periods = sorted([period for period, ok in period_successes.items() if ok])
    for period in success_periods:
        if not args.skip_dbt:
            post_runs.append(
                _run_job(
                    label="dbt_build",
                    fn=POST_LOAD_RUNNERS["dbt_build"],
                    reference_period=period,
                    force=bool(args.force),
                    dry_run=bool(args.dry_run),
                    timeout_seconds=int(args.timeout_seconds),
                    max_retries=int(args.max_retries),
                    phase="post_load",
                )
            )
        if not args.skip_quality:
            post_runs.append(
                _run_job(
                    label="quality_suite",
                    fn=POST_LOAD_RUNNERS["quality_suite"],
                    reference_period=period,
                    force=bool(args.force),
                    dry_run=bool(args.dry_run),
                    timeout_seconds=int(args.timeout_seconds),
                    max_retries=int(args.max_retries),
                    phase="post_load",
                )
            )

    all_executions = executions + post_runs
    accepted_statuses = {"success"}
    if args.allow_blocked:
        accepted_statuses.add("blocked")
    failures = [item for item in all_executions if str(item["status"]) not in accepted_statuses]

    report = {
        "generated_at_utc": now_utc.isoformat(),
        "config": {
            "dry_run": bool(args.dry_run),
            "force": bool(args.force),
            "include_partial": bool(args.include_partial),
            "stale_after_hours": int(args.stale_after_hours),
            "skip_dbt": bool(args.skip_dbt),
            "skip_quality": bool(args.skip_quality),
            "allow_blocked": bool(args.allow_blocked),
            "timeout_seconds": int(args.timeout_seconds),
            "max_retries": int(args.max_retries),
        },
        "selected_jobs": sorted(selected_jobs, key=_job_order),
        "reprocess": {
            "jobs": sorted(reprocess_jobs),
            "periods": sorted(reprocess_periods),
        },
        "plan": plan,
        "executions": all_executions,
        "summary": {
            "planned_pairs": len(plan),
            "executed_pairs": len(executions),
            "skipped_pairs": len([item for item in plan if not item["execute"]]),
            "post_load_runs": len(post_runs),
            "execution_status": _summarize_status(all_executions),
        },
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "Incremental backfill summary:"
        f" planned={report['summary']['planned_pairs']}"
        f" executed={report['summary']['executed_pairs']}"
        f" skipped={report['summary']['skipped_pairs']}"
        f" post_load={report['summary']['post_load_runs']}"
    )
    print(json.dumps(report["summary"]["execution_status"], ensure_ascii=False, indent=2))
    print(f"Report written to {output_path.as_posix()}")

    if failures:
        print(f"Finished with {len(failures)} non-success run(s).")
        return 1
    print("Finished with all executions successful.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
