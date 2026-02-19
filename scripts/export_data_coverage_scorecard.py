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

from app.ops_readiness import build_backend_readiness_report  # noqa: E402
from app.settings import get_settings  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export weekly data coverage scorecard based on contract-level "
            "robustness metrics."
        )
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=7,
        help="Window (days) used for operational metrics (default: 7).",
    )
    parser.add_argument(
        "--slo1-target-pct",
        type=float,
        default=95.0,
        help="SLO-1 target percentage for implemented connectors (default: 95.0).",
    )
    parser.add_argument(
        "--health-window-days",
        type=int,
        default=1,
        help="Current health window in days (default: 1).",
    )
    parser.add_argument(
        "--include-blocked-as-success",
        action="store_true",
        help="Treat blocked runs as success in SLO-1 metrics.",
    )
    parser.add_argument(
        "--output-json",
        default="data/reports/data_coverage_scorecard.json",
        help="Path to output JSON report.",
    )
    return parser.parse_args(argv)


def _source_period_coverage(conn: sa.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        sa.text(
            """
            SELECT source, reference_period, COUNT(*)::bigint AS rows
            FROM silver.fact_indicator
            GROUP BY source, reference_period
            ORDER BY source, reference_period
            """
        )
    ).mappings()
    return [dict(row) for row in rows]


def _run(window_days: int, slo1_target_pct: float, health_window_days: int, include_blocked_as_success: bool) -> dict[str, Any]:
    settings = get_settings()
    engine = sa.create_engine(settings.database_url)
    with engine.begin() as conn:
        scorecard_rows = conn.execute(
            sa.text(
                """
                SELECT
                    metric_group,
                    metric_name,
                    observed_value,
                    target_value,
                    comparator,
                    unit,
                    status
                FROM ops.v_data_coverage_scorecard
                ORDER BY metric_group, metric_name
                """
            )
        ).mappings()
        metrics = [dict(row) for row in scorecard_rows]

        readiness = build_backend_readiness_report(
            conn,
            window_days=window_days,
            slo1_target_pct=slo1_target_pct,
            health_window_days=health_window_days,
            include_blocked_as_success=include_blocked_as_success,
        )

        status_counts = {"pass": 0, "warn": 0}
        for item in metrics:
            status = str(item.get("status", "warn"))
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1

        return {
            "generated_at_utc": datetime.now(tz=UTC).isoformat(),
            "municipality_ibge_code": settings.municipality_ibge_code,
            "window_days": window_days,
            "scorecard": {
                "metrics": metrics,
                "status_counts": status_counts,
            },
            "indicator_source_period_coverage": _source_period_coverage(conn),
            "readiness": readiness,
        }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = _run(
        window_days=max(1, int(args.window_days)),
        slo1_target_pct=float(args.slo1_target_pct),
        health_window_days=max(1, int(args.health_window_days)),
        include_blocked_as_success=bool(args.include_blocked_as_success),
    )

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    pass_count = int(report["scorecard"]["status_counts"].get("pass", 0))
    warn_count = int(report["scorecard"]["status_counts"].get("warn", 0))
    print(
        "Data coverage scorecard exported: "
        f"pass={pass_count} warn={warn_count} file={out_path.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
