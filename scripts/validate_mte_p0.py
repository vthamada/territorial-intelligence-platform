from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    src_str = str(SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

from pipelines.ibge_admin import run as run_ibge_admin
from pipelines.mte_labor import run as run_mte_labor


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate P0 acceptance for labor_mte_fetch by running consecutive "
            "real executions and summarizing outcomes."
        )
    )
    parser.add_argument("--reference-period", required=True, help="Reference period (YYYY or YYYY-MM).")
    parser.add_argument("--runs", type=int, default=3, help="Number of consecutive runs (default: 3).")
    parser.add_argument(
        "--bootstrap-municipality",
        action="store_true",
        help="Run ibge_admin_fetch before MTE runs to ensure municipality context exists.",
    )
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries per connector call.")
    parser.add_argument("--timeout-seconds", type=int, default=30, help="Request timeout in seconds.")
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Emit full JSON report to stdout.",
    )
    return parser


def _run_validation(args: argparse.Namespace) -> dict[str, Any]:
    started_at = datetime.now(UTC)
    report: dict[str, Any] = {
        "reference_period": args.reference_period,
        "requested_runs": args.runs,
        "bootstrap_municipality": bool(args.bootstrap_municipality),
        "started_at_utc": started_at.isoformat().replace("+00:00", "Z"),
        "bootstrap_result": None,
        "runs": [],
    }

    if args.bootstrap_municipality:
        report["bootstrap_result"] = run_ibge_admin(
            reference_period=args.reference_period,
            dry_run=False,
            max_retries=args.max_retries,
            timeout_seconds=args.timeout_seconds,
        )

    for index in range(args.runs):
        result = run_mte_labor(
            reference_period=args.reference_period,
            dry_run=False,
            max_retries=args.max_retries,
            timeout_seconds=args.timeout_seconds,
        )
        report["runs"].append(
            {
                "attempt": index + 1,
                "status": result.get("status"),
                "rows_extracted": result.get("rows_extracted"),
                "rows_written": result.get("rows_written"),
                "warnings": result.get("warnings", []),
                "errors": result.get("errors", []),
                "run_id": result.get("run_id"),
            }
        )

    successful = [run for run in report["runs"] if run["status"] == "success"]
    report["successful_runs"] = len(successful)
    report["all_successful"] = len(successful) == args.runs
    report["finished_at_utc"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.runs <= 0:
        parser.error("--runs must be >= 1")

    report = _run_validation(args)
    summary = (
        f"MTE P0 validation: {report['successful_runs']}/{report['requested_runs']} "
        "successful runs."
    )
    print(summary)
    if args.output_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report["all_successful"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
