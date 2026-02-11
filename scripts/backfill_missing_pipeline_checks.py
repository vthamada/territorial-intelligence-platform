from __future__ import annotations

import argparse
import sys
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

CHECK_NAME = "legacy_run_missing_checks_backfill"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill ops.pipeline_checks for implemented runs that have no checks. "
            "Dry-run by default; use --apply to insert backfill checks."
        )
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="Lookback window for runs in days (default: 30).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply insertions. Without this flag, script only reports candidates.",
    )
    return parser


def _missing_runs(conn: sa.Connection, *, window_days: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        sa.text(
            """
            WITH implemented AS (
                SELECT connector_name
                FROM ops.connector_registry
                WHERE status = 'implemented'
            )
            SELECT
                pr.run_id::text AS run_id,
                pr.job_name,
                pr.status,
                pr.started_at_utc,
                pr.finished_at_utc
            FROM ops.pipeline_runs pr
            JOIN implemented i ON i.connector_name = pr.job_name
            LEFT JOIN ops.pipeline_checks pc ON pc.run_id = pr.run_id
            WHERE pr.started_at_utc >= NOW() - make_interval(days => :window_days)
            GROUP BY pr.run_id, pr.job_name, pr.status, pr.started_at_utc, pr.finished_at_utc
            HAVING COUNT(pc.check_id) = 0
            ORDER BY pr.started_at_utc DESC
            """
        ),
        {"window_days": window_days},
    ).mappings().all()
    return [dict(row) for row in rows]


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = get_settings()
    engine = sa.create_engine(settings.database_url)

    with engine.begin() as conn:
        candidates = _missing_runs(conn, window_days=args.window_days)
        print(f"Runs without checks in last {args.window_days} day(s): {len(candidates)}")
        for item in candidates[:20]:
            print(
                f" - {item['run_id']} | {item['job_name']} | {item['status']} | "
                f"{item['started_at_utc']}"
            )

        if not args.apply:
            print("Dry-run mode: no backfill inserted. Re-run with --apply to execute.")
            return 0

        if not candidates:
            print("No missing runs found. Nothing to backfill.")
            return 0

        for item in candidates:
            run_status = str(item["status"] or "").strip().lower()
            check_status = "pass" if run_status == "success" else "warn"
            details = (
                "Backfilled check for legacy run without recorded pipeline checks. "
                f"Original run_status={run_status or 'unknown'}."
            )
            conn.execute(
                sa.text(
                    """
                    INSERT INTO ops.pipeline_checks (
                        run_id,
                        check_name,
                        status,
                        details,
                        observed_value,
                        threshold_value,
                        created_at_utc
                    )
                    VALUES (
                        CAST(:run_id AS uuid),
                        :check_name,
                        :status,
                        :details,
                        :observed_value,
                        :threshold_value,
                        COALESCE(
                            CAST(:finished_at_utc AS TIMESTAMPTZ),
                            CAST(:started_at_utc AS TIMESTAMPTZ),
                            NOW()
                        )
                    )
                    """
                ),
                {
                    "run_id": item["run_id"],
                    "check_name": CHECK_NAME,
                    "status": check_status,
                    "details": details,
                    "observed_value": 0,
                    "threshold_value": 1,
                    "started_at_utc": item["started_at_utc"],
                    "finished_at_utc": item["finished_at_utc"],
                },
            )

        print(f"Inserted backfill checks: {len(candidates)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
