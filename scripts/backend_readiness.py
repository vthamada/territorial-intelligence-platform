from __future__ import annotations

import argparse
import json
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

from app.ops_readiness import build_backend_readiness_report  # noqa: E402
from app.settings import get_settings  # noqa: E402


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
        "--health-window-days",
        type=int,
        default=1,
        help=(
            "Short window in days used to evaluate current operational health "
            "(default: 1)."
        ),
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


def build_report(
    *,
    window_days: int,
    slo1_target_pct: float,
    health_window_days: int,
    include_blocked_as_success: bool,
) -> dict[str, Any]:
    settings = get_settings()
    engine = sa.create_engine(settings.database_url)
    with engine.connect() as conn:
        conn.execute(sa.text("SELECT 1")).scalar_one()
        return build_backend_readiness_report(
            conn,
            window_days=window_days,
            slo1_target_pct=slo1_target_pct,
            health_window_days=health_window_days,
            include_blocked_as_success=include_blocked_as_success,
        )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    report = build_report(
        window_days=args.window_days,
        slo1_target_pct=args.slo1_target_pct,
        health_window_days=max(1, int(args.health_window_days)),
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
