from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    src_str = str(SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

from app.settings import get_settings  # noqa: E402

REQUIRED_TABLES: tuple[tuple[str, str], ...] = (
    ("silver", "dim_territory"),
    ("silver", "fact_indicator"),
    ("silver", "fact_electorate"),
    ("silver", "fact_election_result"),
    ("ops", "pipeline_runs"),
    ("ops", "pipeline_checks"),
    ("ops", "connector_registry"),
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate backend operational readiness against core contract checks "
            "(schema, ops tracking, SLO-1 and legacy probe signals)."
        )
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=7,
        help="Time window in days used for SLO checks (default: 7).",
    )
    parser.add_argument(
        "--slo1-target-pct",
        type=float,
        default=95.0,
        help="Target success rate (percent) for implemented jobs (default: 95.0).",
    )
    parser.add_argument(
        "--include-blocked-as-success",
        action="store_true",
        help="Treat blocked runs as success in SLO-1 calculation.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when warnings exist (not only hard failures).",
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Print full JSON report.",
    )
    return parser


def _required_tables_report(conn: sa.Connection) -> dict[str, Any]:
    rows = conn.execute(
        sa.text(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
              AND (table_schema, table_name) IN (
                    ('silver', 'dim_territory'),
                    ('silver', 'fact_indicator'),
                    ('silver', 'fact_electorate'),
                    ('silver', 'fact_election_result'),
                    ('ops', 'pipeline_runs'),
                    ('ops', 'pipeline_checks'),
                    ('ops', 'connector_registry')
              )
            """
        )
    ).fetchall()
    found = {(str(row[0]), str(row[1])) for row in rows}
    missing = [
        {"schema": schema, "table": table}
        for schema, table in REQUIRED_TABLES
        if (schema, table) not in found
    ]
    return {
        "required": [{"schema": schema, "table": table} for schema, table in REQUIRED_TABLES],
        "found_count": len(found),
        "missing": missing,
    }


def _connector_registry_report(conn: sa.Connection) -> dict[str, Any]:
    rows = conn.execute(
        sa.text(
            """
            SELECT status::text AS status, COUNT(*) AS count
            FROM ops.connector_registry
            GROUP BY status::text
            ORDER BY status::text
            """
        )
    ).fetchall()
    by_status = {str(row[0]): int(row[1]) for row in rows}
    implemented = conn.execute(
        sa.text(
            """
            SELECT connector_name
            FROM ops.connector_registry
            WHERE status = 'implemented'
            ORDER BY connector_name
            """
        )
    ).fetchall()
    return {
        "total": int(sum(by_status.values())),
        "by_status": by_status,
        "implemented_jobs": [str(row[0]) for row in implemented],
    }


def _slo1_report(
    conn: sa.Connection,
    *,
    window_days: int,
    target_pct: float,
    include_blocked_as_success: bool,
) -> dict[str, Any]:
    rows = conn.execute(
        sa.text(
            """
            WITH implemented AS (
                SELECT connector_name
                FROM ops.connector_registry
                WHERE status = 'implemented'
            )
            SELECT
                pr.job_name,
                COUNT(*) AS total_runs,
                SUM(
                    CASE
                        WHEN :include_blocked_as_success
                            THEN CASE WHEN pr.status IN ('success', 'blocked') THEN 1 ELSE 0 END
                        ELSE CASE WHEN pr.status = 'success' THEN 1 ELSE 0 END
                    END
                ) AS successful_runs
            FROM ops.pipeline_runs pr
            JOIN implemented i ON i.connector_name = pr.job_name
            WHERE pr.started_at_utc >= NOW() - make_interval(days => :window_days)
            GROUP BY pr.job_name
            ORDER BY pr.job_name
            """
        ),
        {
            "window_days": window_days,
            "include_blocked_as_success": include_blocked_as_success,
        },
    ).fetchall()

    items: list[dict[str, Any]] = []
    total_runs = 0
    total_success = 0
    for row in rows:
        job_name = str(row[0])
        job_total = int(row[1] or 0)
        job_success = int(row[2] or 0)
        success_rate = (100.0 * job_success / job_total) if job_total > 0 else 0.0
        total_runs += job_total
        total_success += job_success
        items.append(
            {
                "job_name": job_name,
                "total_runs": job_total,
                "successful_runs": job_success,
                "success_rate_pct": round(success_rate, 2),
                "meets_target": success_rate >= target_pct,
            }
        )

    aggregate_rate = (100.0 * total_success / total_runs) if total_runs > 0 else 0.0
    below_target_jobs = [item["job_name"] for item in items if not item["meets_target"]]

    return {
        "window_days": window_days,
        "target_pct": target_pct,
        "include_blocked_as_success": include_blocked_as_success,
        "total_runs": total_runs,
        "successful_runs": total_success,
        "success_rate_pct": round(aggregate_rate, 2),
        "meets_target": aggregate_rate >= target_pct and total_runs > 0,
        "below_target_jobs": below_target_jobs,
        "items": items,
    }


def _slo3_ops_tracking_report(conn: sa.Connection, *, window_days: int) -> dict[str, Any]:
    total_runs = conn.execute(
        sa.text(
            """
            WITH implemented AS (
                SELECT connector_name
                FROM ops.connector_registry
                WHERE status = 'implemented'
            )
            SELECT COUNT(*)
            FROM ops.pipeline_runs pr
            JOIN implemented i ON i.connector_name = pr.job_name
            WHERE pr.started_at_utc >= NOW() - make_interval(days => :window_days)
            """
        ),
        {"window_days": window_days},
    ).scalar_one()

    runs_with_checks = conn.execute(
        sa.text(
            """
            WITH implemented AS (
                SELECT connector_name
                FROM ops.connector_registry
                WHERE status = 'implemented'
            )
            SELECT COUNT(DISTINCT pr.run_id)
            FROM ops.pipeline_runs pr
            JOIN implemented i ON i.connector_name = pr.job_name
            JOIN ops.pipeline_checks pc ON pc.run_id = pr.run_id
            WHERE pr.started_at_utc >= NOW() - make_interval(days => :window_days)
            """
        ),
        {"window_days": window_days},
    ).scalar_one()

    missing_runs = conn.execute(
        sa.text(
            """
            WITH implemented AS (
                SELECT connector_name
                FROM ops.connector_registry
                WHERE status = 'implemented'
            )
            SELECT pr.run_id::text
            FROM ops.pipeline_runs pr
            JOIN implemented i ON i.connector_name = pr.job_name
            LEFT JOIN ops.pipeline_checks pc ON pc.run_id = pr.run_id
            WHERE pr.started_at_utc >= NOW() - make_interval(days => :window_days)
            GROUP BY pr.run_id
            HAVING COUNT(pc.check_id) = 0
            ORDER BY pr.run_id
            LIMIT 10
            """
        ),
        {"window_days": window_days},
    ).fetchall()

    total_runs_int = int(total_runs or 0)
    runs_with_checks_int = int(runs_with_checks or 0)
    missing_count = total_runs_int - runs_with_checks_int
    return {
        "window_days": window_days,
        "total_runs": total_runs_int,
        "runs_with_checks": runs_with_checks_int,
        "runs_missing_checks": max(0, missing_count),
        "meets_target": total_runs_int == runs_with_checks_int,
        "sample_missing_run_ids": [str(row[0]) for row in missing_runs],
    }


def _source_probe_report(conn: sa.Connection) -> dict[str, Any]:
    rows = conn.execute(
        sa.text(
            """
            SELECT source, COUNT(*) AS count
            FROM silver.fact_indicator
            WHERE indicator_code LIKE '%_SOURCE_PROBE'
            GROUP BY source
            ORDER BY source
            """
        )
    ).fetchall()
    by_source = {str(row[0]): int(row[1]) for row in rows}
    return {"total_rows": int(sum(by_source.values())), "by_source": by_source}


def build_report(
    *,
    window_days: int,
    slo1_target_pct: float,
    include_blocked_as_success: bool,
) -> dict[str, Any]:
    settings = get_settings()
    engine = sa.create_engine(settings.database_url)
    now_utc = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    hard_failures: list[str] = []
    warnings: list[str] = []

    with engine.connect() as conn:
        conn.execute(sa.text("SELECT 1")).scalar_one()
        postgis_version = conn.execute(
            sa.text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
        ).scalar_one_or_none()

        tables_report = _required_tables_report(conn)
        registry_report = _connector_registry_report(conn)
        slo1_report = _slo1_report(
            conn,
            window_days=window_days,
            target_pct=slo1_target_pct,
            include_blocked_as_success=include_blocked_as_success,
        )
        slo3_report = _slo3_ops_tracking_report(conn, window_days=window_days)
        source_probe_report = _source_probe_report(conn)

    if postgis_version is None:
        hard_failures.append("PostGIS extension is not installed.")

    if tables_report["missing"]:
        missing_tokens = [f"{item['schema']}.{item['table']}" for item in tables_report["missing"]]
        hard_failures.append("Missing required tables: " + ", ".join(missing_tokens))

    if registry_report["total"] == 0:
        hard_failures.append("Connector registry is empty.")

    if not slo3_report["meets_target"]:
        hard_failures.append(
            "SLO-3 violated: some implemented runs do not have pipeline checks."
        )

    if slo1_report["total_runs"] == 0:
        warnings.append("SLO-1 has no implemented runs in the selected window.")
    elif not slo1_report["meets_target"]:
        warnings.append(
            f"SLO-1 below target: {slo1_report['success_rate_pct']}% < {slo1_target_pct:.1f}%."
        )

    if source_probe_report["total_rows"] > 0:
        warnings.append(
            "Legacy *_SOURCE_PROBE rows are still present in silver.fact_indicator."
        )

    return {
        "generated_at_utc": now_utc,
        "window_days": window_days,
        "postgis": {
            "installed": postgis_version is not None,
            "version": postgis_version,
        },
        "required_tables": tables_report,
        "connector_registry": registry_report,
        "slo1": slo1_report,
        "slo3": slo3_report,
        "source_probe": source_probe_report,
        "hard_failures": hard_failures,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    report = build_report(
        window_days=args.window_days,
        slo1_target_pct=args.slo1_target_pct,
        include_blocked_as_success=bool(args.include_blocked_as_success),
    )

    is_ready = not report["hard_failures"] and (not args.strict or not report["warnings"])

    summary = (
        "Backend readiness: "
        + ("READY" if is_ready else "NOT READY")
        + f" | hard_failures={len(report['hard_failures'])}"
        + f" | warnings={len(report['warnings'])}"
    )
    print(summary)
    if report["hard_failures"]:
        for item in report["hard_failures"]:
            print(f"HARD_FAIL: {item}")
    if report["warnings"]:
        for item in report["warnings"]:
            print(f"WARN: {item}")

    if args.output_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))

    return 0 if is_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
