from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import sqlalchemy as sa

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    src_str = str(SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

from app.ops_robustness_window import build_ops_robustness_window_report  # noqa: E402
from app.settings import get_settings  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export consolidated operational robustness report for a target window "
            "(default: 30 days)."
        )
    )
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--health-window-days", type=int, default=7)
    parser.add_argument("--slo1-target-pct", type=float, default=95.0)
    parser.add_argument(
        "--include-blocked-as-success",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--output-json",
        default="data/reports/ops_robustness_window_30d.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    settings = get_settings()
    engine = sa.create_engine(settings.database_url)

    with engine.connect() as conn:
        report = build_ops_robustness_window_report(
            conn,
            window_days=max(1, int(args.window_days)),
            health_window_days=max(1, int(args.health_window_days)),
            slo1_target_pct=float(args.slo1_target_pct),
            include_blocked_as_success=bool(args.include_blocked_as_success),
            strict=bool(args.strict),
        )

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print(
        "Ops robustness window exported:"
        f" status={report['status']}"
        f" severity={report['severity']}"
        f" all_pass={report['gates']['all_pass']}"
        f" file={output_path.as_posix()}"
    )
    return 0 if report["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
