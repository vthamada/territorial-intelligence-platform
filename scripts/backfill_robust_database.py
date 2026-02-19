from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import sqlalchemy as sa
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    src_str = str(SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

from app.settings import get_settings  # noqa: E402
from pipelines.quality_suite import run as run_quality_suite  # noqa: E402
from pipelines.sejusp_public_safety import run as run_sejusp_public_safety  # noqa: E402
from pipelines.senatran_fleet import run as run_senatran_fleet  # noqa: E402
from pipelines.sidra_indicators import run as run_sidra_indicators  # noqa: E402
from pipelines.siops_health_finance import run as run_siops_health_finance  # noqa: E402
from pipelines.snis_sanitation import run as run_snis_sanitation  # noqa: E402
from pipelines.inmet_climate import run as run_inmet_climate  # noqa: E402
from pipelines.inpe_queimadas import run as run_inpe_queimadas  # noqa: E402
from pipelines.ana_hydrology import run as run_ana_hydrology  # noqa: E402
from pipelines.anatel_connectivity import run as run_anatel_connectivity  # noqa: E402
from pipelines.aneel_energy import run as run_aneel_energy  # noqa: E402
from pipelines.cecad_social_protection import run as run_cecad_social_protection  # noqa: E402
from pipelines.censo_suas import run as run_censo_suas  # noqa: E402
from pipelines.urban_roads import run as run_urban_roads  # noqa: E402
from pipelines.urban_pois import run as run_urban_pois  # noqa: E402
from pipelines.ibge_admin import run as run_ibge_admin  # noqa: E402
from pipelines.ibge_geometries import run as run_ibge_geometries  # noqa: E402
from pipelines.tse_catalog import run as run_tse_catalog  # noqa: E402
from pipelines.tse_electorate import run as run_tse_electorate  # noqa: E402
from pipelines.tse_results import run as run_tse_results  # noqa: E402


def _parse_csv_values(raw: str) -> list[str]:
    values = [item.strip() for item in raw.split(",")]
    return [item for item in values if item]


def _normalize_tse_years(values: list[str]) -> list[str]:
    parsed: set[int] = set()
    for value in values:
        try:
            parsed.add(int(value))
        except ValueError:
            continue
    return [str(year) for year in sorted(parsed, reverse=True)]


def _sync_connector_registry(database_url: str) -> int:
    config_path = Path("configs/connectors.yml")
    if not config_path.exists():
        raise RuntimeError("Missing configs/connectors.yml")

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    connectors = payload.get("connectors", [])
    if not isinstance(connectors, list):
        connectors = []

    dsn = database_url.replace("+psycopg", "")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for item in connectors:
                if not isinstance(item, dict):
                    continue
                cur.execute(
                    """
                    INSERT INTO ops.connector_registry (
                        connector_name,
                        source,
                        wave,
                        status,
                        notes
                    ) VALUES (
                        %(connector_name)s,
                        %(source)s,
                        %(wave)s,
                        %(status)s,
                        %(notes)s
                    )
                    ON CONFLICT (connector_name) DO UPDATE SET
                        source = EXCLUDED.source,
                        wave = EXCLUDED.wave,
                        status = EXCLUDED.status,
                        notes = EXCLUDED.notes,
                        updated_at_utc = NOW()
                    """,
                    {
                        "connector_name": item.get("connector_name"),
                        "source": item.get("source"),
                        "wave": item.get("wave"),
                        "status": item.get("status"),
                        "notes": item.get("notes"),
                    },
                )
        conn.commit()
    return len(connectors)


def _run_job(
    *,
    label: str,
    fn: Any,
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
    print(f"{label}({reference_period}) => status={status} rows={rows_loaded}")
    return {
        "label": label,
        "reference_period": reference_period,
        "status": status,
        "rows_loaded": rows_loaded,
        "result": result,
    }


def _coverage_report(database_url: str) -> dict[str, Any]:
    engine = sa.create_engine(database_url)
    with engine.begin() as conn:
        electorate = conn.execute(
            sa.text(
                """
                SELECT
                    COUNT(DISTINCT reference_year)::bigint AS distinct_years,
                    MIN(reference_year)::int AS min_year,
                    MAX(reference_year)::int AS max_year,
                    COUNT(*)::bigint AS rows
                FROM silver.fact_electorate
                """
            )
        ).mappings().one()
        election = conn.execute(
            sa.text(
                """
                SELECT
                    COUNT(DISTINCT election_year)::bigint AS distinct_years,
                    MIN(election_year)::int AS min_year,
                    MAX(election_year)::int AS max_year,
                    COUNT(*)::bigint AS rows
                FROM silver.fact_election_result
                """
            )
        ).mappings().one()
        election_zone_rows = conn.execute(
            sa.text(
                """
                SELECT COUNT(*)::bigint AS rows
                FROM silver.fact_election_result fr
                JOIN silver.dim_territory dt ON dt.territory_id = fr.territory_id
                WHERE dt.level::text = 'electoral_zone'
                """
            )
        ).scalar_one()
        indicators_by_source = conn.execute(
            sa.text(
                """
                SELECT source, reference_period, COUNT(*)::bigint AS rows
                FROM silver.fact_indicator
                GROUP BY source, reference_period
                ORDER BY source, reference_period
                """
            )
        ).mappings().all()
        indicators_by_level = conn.execute(
            sa.text(
                """
                SELECT dt.level::text AS level, COUNT(*)::bigint AS rows
                FROM silver.fact_indicator fi
                JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
                GROUP BY dt.level::text
                ORDER BY dt.level::text
                """
            )
        ).mappings().all()
        social_protection = conn.execute(
            sa.text(
                """
                SELECT
                    COUNT(*)::bigint AS rows,
                    COUNT(DISTINCT reference_period)::bigint AS distinct_periods
                FROM silver.fact_social_protection
                """
            )
        ).mappings().one()
        social_assistance_network = conn.execute(
            sa.text(
                """
                SELECT
                    COUNT(*)::bigint AS rows,
                    COUNT(DISTINCT reference_period)::bigint AS distinct_periods
                FROM silver.fact_social_assistance_network
                """
            )
        ).mappings().one()
        urban_roads = conn.execute(
            sa.text(
                """
                SELECT COUNT(*)::bigint AS rows
                FROM map.urban_road_segment
                """
            )
        ).mappings().one()
        urban_pois = conn.execute(
            sa.text(
                """
                SELECT COUNT(*)::bigint AS rows
                FROM map.urban_poi
                """
            )
        ).mappings().one()

    return {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "electorate": dict(electorate),
        "election_result": {
            **dict(election),
            "electoral_zone_rows": int(election_zone_rows or 0),
        },
        "indicator_by_source_period": [dict(row) for row in indicators_by_source],
        "indicator_by_level": [dict(row) for row in indicators_by_level],
        "social_protection": dict(social_protection),
        "social_assistance_network": dict(social_assistance_network),
        "urban_roads": dict(urban_roads),
        "urban_pois": dict(urban_pois),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill key historical datasets and strategic sources to harden "
            "database coverage for territorial intelligence."
        )
    )
    parser.add_argument("--tse-years", default="2024,2022,2020,2018,2016")
    parser.add_argument("--indicator-periods", default="2025")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-wave1", action="store_true")
    parser.add_argument("--skip-tse", action="store_true")
    parser.add_argument("--skip-wave4", action="store_true")
    parser.add_argument("--skip-wave5", action="store_true")
    parser.add_argument("--include-wave6", action="store_true")
    parser.add_argument("--include-wave7", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--output-json", default="")
    args = parser.parse_args(argv)

    settings = get_settings()
    print("Synchronizing connector registry...")
    synced_count = _sync_connector_registry(settings.database_url)
    print(f"Synchronized {synced_count} connectors into ops.connector_registry.")

    executions: list[dict[str, Any]] = []
    wave1_reference = next(
        iter(_parse_csv_values(args.indicator_periods) or _parse_csv_values(args.tse_years) or ["2025"])
    )
    if not args.skip_wave1:
        executions.append(
            _run_job(
                label="ibge_admin_fetch",
                fn=run_ibge_admin,
                reference_period=wave1_reference,
                dry_run=args.dry_run,
                timeout_seconds=args.timeout_seconds,
                max_retries=args.max_retries,
            )
        )
        executions.append(
            _run_job(
                label="ibge_geometries_fetch",
                fn=run_ibge_geometries,
                reference_period=wave1_reference,
                dry_run=args.dry_run,
                timeout_seconds=args.timeout_seconds,
                max_retries=args.max_retries,
            )
        )

    tse_years = _normalize_tse_years(_parse_csv_values(args.tse_years))
    if not args.skip_tse and not tse_years:
        raise RuntimeError("No valid TSE years were provided in --tse-years.")
    if not args.skip_tse:
        print(f"TSE years selected for backfill: {', '.join(tse_years)}")
        for year in tse_years:
            executions.append(
                _run_job(
                    label="tse_catalog_discovery",
                    fn=run_tse_catalog,
                    reference_period=year,
                    dry_run=args.dry_run,
                    timeout_seconds=args.timeout_seconds,
                    max_retries=args.max_retries,
                )
            )
            executions.append(
                _run_job(
                    label="tse_electorate_fetch",
                    fn=run_tse_electorate,
                    reference_period=year,
                    dry_run=args.dry_run,
                    timeout_seconds=args.timeout_seconds,
                    max_retries=args.max_retries,
                )
            )
            executions.append(
                _run_job(
                    label="tse_results_fetch",
                    fn=run_tse_results,
                    reference_period=year,
                    dry_run=args.dry_run,
                    timeout_seconds=args.timeout_seconds,
                    max_retries=args.max_retries,
                )
            )

    connector_wave4 = [
        ("sidra_indicators_fetch", run_sidra_indicators),
        ("senatran_fleet_fetch", run_senatran_fleet),
        ("sejusp_public_safety_fetch", run_sejusp_public_safety),
        ("siops_health_finance_fetch", run_siops_health_finance),
        ("snis_sanitation_fetch", run_snis_sanitation),
    ]
    connector_wave5 = [
        ("inmet_climate_fetch", run_inmet_climate),
        ("inpe_queimadas_fetch", run_inpe_queimadas),
        ("ana_hydrology_fetch", run_ana_hydrology),
        ("anatel_connectivity_fetch", run_anatel_connectivity),
        ("aneel_energy_fetch", run_aneel_energy),
    ]
    connector_wave6 = [
        ("cecad_social_protection_fetch", run_cecad_social_protection),
        ("censo_suas_fetch", run_censo_suas),
    ]
    connector_wave7 = [
        ("urban_roads_fetch", run_urban_roads),
        ("urban_pois_fetch", run_urban_pois),
    ]

    for period in _parse_csv_values(args.indicator_periods):
        if not args.skip_wave4:
            for label, fn in connector_wave4:
                executions.append(
                    _run_job(
                        label=label,
                        fn=fn,
                        reference_period=period,
                        dry_run=args.dry_run,
                        timeout_seconds=args.timeout_seconds,
                        max_retries=args.max_retries,
                    )
                )
        if not args.skip_wave5:
            for label, fn in connector_wave5:
                executions.append(
                    _run_job(
                        label=label,
                        fn=fn,
                        reference_period=period,
                        dry_run=args.dry_run,
                        timeout_seconds=args.timeout_seconds,
                        max_retries=args.max_retries,
                    )
                )
        if args.include_wave6:
            for label, fn in connector_wave6:
                executions.append(
                    _run_job(
                        label=label,
                        fn=fn,
                        reference_period=period,
                        dry_run=args.dry_run,
                        timeout_seconds=args.timeout_seconds,
                        max_retries=args.max_retries,
                    )
                )
        if args.include_wave7:
            for label, fn in connector_wave7:
                executions.append(
                    _run_job(
                        label=label,
                        fn=fn,
                        reference_period=period,
                        dry_run=args.dry_run,
                        timeout_seconds=args.timeout_seconds,
                        max_retries=args.max_retries,
                    )
                )

        executions.append(
            _run_job(
                label="quality_suite",
                fn=run_quality_suite,
                reference_period=period,
                dry_run=args.dry_run,
                timeout_seconds=args.timeout_seconds,
                max_retries=args.max_retries,
            )
        )

    report = {
        "executions": executions,
        "coverage": _coverage_report(settings.database_url),
    }

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Coverage report written to {out_path.as_posix()}")

    print(
        "Coverage summary:"
        f" electorate_years={report['coverage']['electorate']['distinct_years']}"
        f" election_years={report['coverage']['election_result']['distinct_years']}"
        f" election_zone_rows={report['coverage']['election_result']['electoral_zone_rows']}"
    )

    failed = [item for item in executions if item["status"] not in {"success"}]
    if failed:
        print(f"Finished with {len(failed)} non-success execution(s).")
        return 1
    print("Finished with all executions successful.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
