from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import sqlalchemy as sa

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
SCRIPTS_PATH = PROJECT_ROOT / "scripts"
if SRC_PATH.exists():
    src_str = str(SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
if SCRIPTS_PATH.exists():
    scripts_str = str(SCRIPTS_PATH)
    if scripts_str not in sys.path:
        sys.path.insert(0, scripts_str)

from app.settings import get_settings  # noqa: E402
from pipelines.ana_hydrology import run as run_ana_hydrology  # noqa: E402
from pipelines.inmet_climate import run as run_inmet_climate  # noqa: E402
from pipelines.inpe_queimadas import run as run_inpe_queimadas  # noqa: E402
from pipelines.quality_suite import run as run_quality_suite  # noqa: E402
import bootstrap_manual_sources as bootstrap_manual_sources_module  # noqa: E402

_ENV_SOURCE_NAMES = ("INMET", "INPE_QUEIMADAS", "ANA")
_ENV_JOBS: tuple[tuple[str, Callable[..., dict[str, Any]]], ...] = (
    ("inmet_climate_fetch", run_inmet_climate),
    ("inpe_queimadas_fetch", run_inpe_queimadas),
    ("ana_hydrology_fetch", run_ana_hydrology),
)
_BOOTSTRAP_SOURCES: tuple[
    tuple[str, Callable[..., Any]],
    ...,
] = (
    ("INMET", bootstrap_manual_sources_module.bootstrap_inmet),
    ("INPE_QUEIMADAS", bootstrap_manual_sources_module.bootstrap_inpe_queimadas),
    ("ANA", bootstrap_manual_sources_module.bootstrap_ana),
)


def _parse_periods(raw: str) -> list[str]:
    values = [token.strip() for token in str(raw).split(",")]
    years: set[int] = set()
    for token in values:
        if len(token) != 4 or not token.isdigit():
            continue
        years.add(int(token))
    return [str(year) for year in sorted(years)]


def _run_pipeline_job(
    *,
    label: str,
    fn: Callable[..., dict[str, Any]],
    reference_period: str,
    dry_run: bool,
    timeout_seconds: int,
    max_retries: int,
) -> dict[str, Any]:
    result = fn(
        reference_period=reference_period,
        dry_run=dry_run,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    status = str(result.get("status", "unknown"))
    rows_loaded = int(result.get("rows_written", result.get("rows_loaded", 0)) or 0)
    return {
        "job": label,
        "reference_period": reference_period,
        "status": status,
        "rows_loaded": rows_loaded,
        "result": result,
    }


def _run_bootstrap(
    *,
    periods: list[str],
    municipality_name: str,
    municipality_ibge_code: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for period in periods:
        for source_name, bootstrap_fn in _BOOTSTRAP_SOURCES:
            response = bootstrap_fn(
                reference_year=period,
                municipality_name=municipality_name,
                municipality_ibge_code=municipality_ibge_code,
            )
            status = str(getattr(response, "status", "unknown"))
            results.append(
                {
                    "source": source_name,
                    "reference_period": period,
                    "status": status,
                    "output_file": getattr(response, "output_file", None),
                    "details": getattr(response, "details", None) or {},
                    "error": getattr(response, "error", None),
                }
            )
    return results


def _environment_coverage(database_url: str) -> list[dict[str, Any]]:
    engine = sa.create_engine(database_url)
    with engine.begin() as conn:
        rows = conn.execute(
            sa.text(
                """
                SELECT
                    source,
                    COUNT(*)::bigint AS rows,
                    COUNT(DISTINCT reference_period)::bigint AS distinct_periods,
                    MIN(reference_period)::text AS min_period,
                    MAX(reference_period)::text AS max_period
                FROM silver.fact_indicator
                WHERE source IN ('INMET', 'INPE_QUEIMADAS', 'ANA')
                GROUP BY source
                ORDER BY source
                """
            )
        ).mappings().all()
    by_source = {str(item["source"]): dict(item) for item in rows}
    normalized_rows: list[dict[str, Any]] = []
    for source in _ENV_SOURCE_NAMES:
        row = by_source.get(source)
        if row is None:
            normalized_rows.append(
                {
                    "source": source,
                    "rows": 0,
                    "distinct_periods": 0,
                    "min_period": None,
                    "max_period": None,
                }
            )
            continue
        normalized_rows.append(row)
    return normalized_rows


def _summarize_status(results: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in results:
        key = str(item.get("status", "unknown"))
        summary[key] = summary.get(key, 0) + 1
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run BD-050 environment historical backfill for INMET/INPE/ANA "
            "with optional manual bootstrap and consolidated report."
        )
    )
    parser.add_argument("--periods", default="2021,2022,2023,2024,2025")
    parser.add_argument("--municipality-name", default="Diamantina")
    parser.add_argument("--municipality-ibge-code", default="3121605")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-bootstrap", action="store_true")
    parser.add_argument("--skip-quality", action="store_true")
    parser.add_argument("--allow-blocked", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument(
        "--output-json",
        default="data/reports/bd050_environment_history_report.json",
    )
    args = parser.parse_args(argv)

    periods = _parse_periods(args.periods)
    if not periods:
        raise RuntimeError("No valid periods provided. Expected comma-separated years (YYYY).")

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "periods": periods,
        "dry_run": bool(args.dry_run),
        "bootstrap": [],
        "executions": [],
        "quality_runs": [],
        "coverage": [],
        "summary": {},
    }

    if not args.skip_bootstrap:
        report["bootstrap"] = _run_bootstrap(
            periods=periods,
            municipality_name=args.municipality_name,
            municipality_ibge_code=args.municipality_ibge_code,
        )

    for period in periods:
        for label, fn in _ENV_JOBS:
            report["executions"].append(
                _run_pipeline_job(
                    label=label,
                    fn=fn,
                    reference_period=period,
                    dry_run=args.dry_run,
                    timeout_seconds=args.timeout_seconds,
                    max_retries=args.max_retries,
                )
            )
        if not args.skip_quality:
            report["quality_runs"].append(
                _run_pipeline_job(
                    label="quality_suite",
                    fn=run_quality_suite,
                    reference_period=period,
                    dry_run=args.dry_run,
                    timeout_seconds=args.timeout_seconds,
                    max_retries=args.max_retries,
                )
            )

    settings = get_settings()
    report["coverage"] = _environment_coverage(settings.database_url)
    report["summary"] = {
        "bootstrap_status": _summarize_status(report["bootstrap"]),
        "execution_status": _summarize_status(report["executions"]),
        "quality_status": _summarize_status(report["quality_runs"]),
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report written to {output_path.as_posix()}")

    bootstrap_failures = [
        item
        for item in report["bootstrap"]
        if str(item.get("status", "")) in {"error", "failed", "manual_required"}
    ]
    execution_failures = []
    accepted_execution_status = {"success"}
    if args.allow_blocked:
        accepted_execution_status.add("blocked")
    for item in report["executions"]:
        if str(item.get("status", "")) not in accepted_execution_status:
            execution_failures.append(item)
    quality_failures = [
        item for item in report["quality_runs"] if str(item.get("status", "")) != "success"
    ]

    if bootstrap_failures or execution_failures or quality_failures:
        print(
            "BD-050 execution finished with non-success statuses:"
            f" bootstrap={len(bootstrap_failures)}"
            f" executions={len(execution_failures)}"
            f" quality={len(quality_failures)}"
        )
        return 1
    print("BD-050 execution finished successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
