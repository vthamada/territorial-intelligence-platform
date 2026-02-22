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
from app.api.strategic_engine_config import load_strategic_engine_config  # noqa: E402
from pipelines.common.schema_contracts import (  # noqa: E402
    build_schema_contract_records,
    load_connectors,
    load_schema_contract_config,
)
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
from pipelines.urban_transport import run as run_urban_transport  # noqa: E402
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


def _sync_schema_contracts(database_url: str) -> dict[str, int]:
    connectors = load_connectors(Path("configs/connectors.yml"))
    contract_config = load_schema_contract_config(Path("configs/schema_contracts.yml"))
    records = build_schema_contract_records(connectors, config=contract_config)
    dsn = database_url.replace("+psycopg", "")

    inserted_or_updated = 0
    deprecated = 0
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for item in records:
                cur.execute(
                    """
                    UPDATE ops.source_schema_contracts
                    SET status = 'deprecated',
                        updated_at_utc = NOW()
                    WHERE connector_name = %(connector_name)s
                      AND target_table = %(target_table)s
                      AND schema_version <> %(schema_version)s
                      AND status = 'active'
                    """,
                    {
                        "connector_name": item["connector_name"],
                        "target_table": item["target_table"],
                        "schema_version": item["schema_version"],
                    },
                )
                deprecated += int(cur.rowcount or 0)

                cur.execute(
                    """
                    INSERT INTO ops.source_schema_contracts (
                        connector_name,
                        source,
                        dataset,
                        target_table,
                        schema_version,
                        effective_from,
                        status,
                        required_columns,
                        optional_columns,
                        column_types,
                        constraints_json,
                        source_uri,
                        notes
                    ) VALUES (
                        %(connector_name)s,
                        %(source)s,
                        %(dataset)s,
                        %(target_table)s,
                        %(schema_version)s,
                        CAST(%(effective_from)s AS date),
                        %(status)s,
                        CAST(%(required_columns)s AS jsonb),
                        CAST(%(optional_columns)s AS jsonb),
                        CAST(%(column_types)s AS jsonb),
                        CAST(%(constraints_json)s AS jsonb),
                        %(source_uri)s,
                        %(notes)s
                    )
                    ON CONFLICT (connector_name, target_table, schema_version) DO UPDATE SET
                        source = EXCLUDED.source,
                        dataset = EXCLUDED.dataset,
                        effective_from = EXCLUDED.effective_from,
                        status = EXCLUDED.status,
                        required_columns = EXCLUDED.required_columns,
                        optional_columns = EXCLUDED.optional_columns,
                        column_types = EXCLUDED.column_types,
                        constraints_json = EXCLUDED.constraints_json,
                        source_uri = EXCLUDED.source_uri,
                        notes = EXCLUDED.notes,
                        updated_at_utc = NOW()
                    """,
                    {
                        "connector_name": item["connector_name"],
                        "source": item["source"],
                        "dataset": item["dataset"],
                        "target_table": item["target_table"],
                        "schema_version": item["schema_version"],
                        "effective_from": item["effective_from"],
                        "status": item["status"],
                        "required_columns": json.dumps(item["required_columns"], ensure_ascii=False),
                        "optional_columns": json.dumps(item["optional_columns"], ensure_ascii=False),
                        "column_types": json.dumps(item["column_types"], ensure_ascii=False),
                        "constraints_json": json.dumps(item["constraints_json"], ensure_ascii=False),
                        "source_uri": item["source_uri"],
                        "notes": item["notes"],
                    },
                )
                inserted_or_updated += 1
        conn.commit()

    return {
        "prepared": len(records),
        "inserted_or_updated": inserted_or_updated,
        "deprecated": deprecated,
    }


def _sync_strategic_score_versions(database_url: str) -> dict[str, int | str]:
    cfg = load_strategic_engine_config()
    score_version = f"v{cfg.version}"
    dsn = database_url.replace("+psycopg", "")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ops.strategic_score_versions
                SET status = 'deprecated',
                    updated_at_utc = NOW()
                WHERE status = 'active'
                  AND score_version <> %(score_version)s
                """,
                {"score_version": score_version},
            )
            deprecated = int(cur.rowcount or 0)

            cur.execute(
                """
                INSERT INTO ops.strategic_score_versions (
                    score_version,
                    config_version,
                    status,
                    effective_from,
                    scoring_method,
                    critical_threshold,
                    attention_threshold,
                    default_domain_weight,
                    default_indicator_weight,
                    domain_weights,
                    indicator_weights,
                    notes
                ) VALUES (
                    %(score_version)s,
                    %(config_version)s,
                    'active',
                    CURRENT_DATE,
                    'rank_abs_value_v1',
                    %(critical_threshold)s,
                    %(attention_threshold)s,
                    %(default_domain_weight)s,
                    %(default_indicator_weight)s,
                    CAST(%(domain_weights)s AS jsonb),
                    CAST(%(indicator_weights)s AS jsonb),
                    %(notes)s
                )
                ON CONFLICT (score_version) DO UPDATE SET
                    config_version = EXCLUDED.config_version,
                    status = EXCLUDED.status,
                    effective_from = EXCLUDED.effective_from,
                    scoring_method = EXCLUDED.scoring_method,
                    critical_threshold = EXCLUDED.critical_threshold,
                    attention_threshold = EXCLUDED.attention_threshold,
                    default_domain_weight = EXCLUDED.default_domain_weight,
                    default_indicator_weight = EXCLUDED.default_indicator_weight,
                    domain_weights = EXCLUDED.domain_weights,
                    indicator_weights = EXCLUDED.indicator_weights,
                    notes = EXCLUDED.notes,
                    updated_at_utc = NOW()
                """,
                {
                    "score_version": score_version,
                    "config_version": cfg.version,
                    "critical_threshold": cfg.scoring.critical_threshold,
                    "attention_threshold": cfg.scoring.attention_threshold,
                    "default_domain_weight": cfg.scoring.default_domain_weight,
                    "default_indicator_weight": cfg.scoring.default_indicator_weight,
                    "domain_weights": json.dumps(cfg.scoring.domain_weights, ensure_ascii=False),
                    "indicator_weights": json.dumps(cfg.scoring.indicator_weights, ensure_ascii=False),
                    "notes": "Synced from configs/strategic_engine.yml",
                },
            )
            upserted = int(cur.rowcount or 0)
        conn.commit()
    return {
        "score_version": score_version,
        "config_version": cfg.version,
        "upserted": upserted,
        "deprecated": deprecated,
    }


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
        environmental_sources = conn.execute(
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
        urban_transport = conn.execute(
            sa.text(
                """
                SELECT COUNT(*)::bigint AS rows
                FROM map.urban_transport_stop
                """
            )
        ).mappings().one()
        environment_risk = conn.execute(
            sa.text(
                """
                SELECT
                    territory_level,
                    COUNT(*)::bigint AS rows,
                    COUNT(DISTINCT reference_period)::bigint AS distinct_periods,
                    MAX(reference_period)::text AS max_period
                FROM map.v_environment_risk_aggregation
                GROUP BY territory_level
                ORDER BY territory_level
                """
            )
        ).mappings().all()
        environment_risk_mart = conn.execute(
            sa.text(
                """
                SELECT
                    territory_level,
                    COUNT(*)::bigint AS rows,
                    COUNT(DISTINCT reference_period)::bigint AS distinct_periods,
                    MAX(reference_period)::text AS max_period
                FROM gold.mart_environment_risk
                GROUP BY territory_level
                ORDER BY territory_level
                """
            )
        ).mappings().all()
        priority_drivers = conn.execute(
            sa.text(
                """
                SELECT
                    COUNT(*)::bigint AS rows,
                    COUNT(DISTINCT reference_period)::bigint AS distinct_periods,
                    MAX(reference_period)::text AS max_period
                FROM gold.mart_priority_drivers
                """
            )
        ).mappings().one()
        strategic_score_versions = conn.execute(
            sa.text(
                """
                SELECT
                    COUNT(*)::bigint AS total_versions,
                    COUNT(*) FILTER (WHERE status = 'active')::bigint AS active_versions,
                    MAX(score_version)::text AS latest_score_version
                FROM ops.strategic_score_versions
                """
            )
        ).mappings().one()
        schema_contracts = conn.execute(
            sa.text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE cr.status IN ('implemented', 'partial'))::bigint AS expected_connectors,
                    COUNT(*) FILTER (
                        WHERE cr.status IN ('implemented', 'partial')
                          AND ssc.connector_name IS NOT NULL
                    )::bigint AS covered_connectors
                FROM ops.connector_registry cr
                LEFT JOIN (
                    SELECT DISTINCT connector_name
                    FROM ops.v_source_schema_contracts_active
                ) ssc ON ssc.connector_name = cr.connector_name
                WHERE cr.source <> 'INTERNAL'
                  AND cr.connector_name NOT IN ('quality_suite', 'dbt_build', 'tse_catalog_discovery')
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
        "environmental_sources": [dict(row) for row in environmental_sources],
        "indicator_by_level": [dict(row) for row in indicators_by_level],
        "social_protection": dict(social_protection),
        "social_assistance_network": dict(social_assistance_network),
        "urban_roads": dict(urban_roads),
        "urban_pois": dict(urban_pois),
        "urban_transport_stops": dict(urban_transport),
        "environment_risk_aggregation": [dict(row) for row in environment_risk],
        "environment_risk_mart": [dict(row) for row in environment_risk_mart],
        "priority_drivers_mart": dict(priority_drivers),
        "strategic_score_versions": dict(strategic_score_versions),
        "schema_contracts": dict(schema_contracts),
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
    print("Synchronizing source schema contracts...")
    schema_sync = _sync_schema_contracts(settings.database_url)
    print(
        "Synchronized source schema contracts:"
        f" prepared={schema_sync['prepared']}"
        f" upserted={schema_sync['inserted_or_updated']}"
        f" deprecated={schema_sync['deprecated']}"
    )
    print("Synchronizing strategic score versions...")
    score_version_sync = _sync_strategic_score_versions(settings.database_url)
    print(
        "Synchronized strategic score version:"
        f" score_version={score_version_sync['score_version']}"
        f" config_version={score_version_sync['config_version']}"
        f" upserted={score_version_sync['upserted']}"
        f" deprecated={score_version_sync['deprecated']}"
    )

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
        ("urban_transport_fetch", run_urban_transport),
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
