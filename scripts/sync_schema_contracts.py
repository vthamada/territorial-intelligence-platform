from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    src_str = str(SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

from app.settings import get_settings  # noqa: E402
from pipelines.common.schema_contracts import (  # noqa: E402
    build_schema_contract_records,
    load_connectors,
    load_schema_contract_config,
)


def _sync_schema_contracts(
    *,
    dsn: str,
    records: list[dict[str, Any]],
) -> dict[str, int]:
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
        "inserted_or_updated": inserted_or_updated,
        "deprecated": deprecated,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync versioned source schema contracts into ops.source_schema_contracts."
    )
    parser.add_argument("--connectors", default="configs/connectors.yml")
    parser.add_argument("--contracts-config", default="configs/schema_contracts.yml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-json", default="")
    args = parser.parse_args(argv)

    settings = get_settings()
    connectors_path = Path(args.connectors)
    contract_config_path = Path(args.contracts_config)

    connectors = load_connectors(connectors_path)
    contract_config = load_schema_contract_config(contract_config_path)
    records = build_schema_contract_records(
        connectors,
        config=contract_config,
        now_utc=datetime.now(UTC),
    )

    summary: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "connectors_loaded": len(connectors),
        "contracts_prepared": len(records),
        "dry_run": bool(args.dry_run),
    }

    if not args.dry_run:
        dsn = settings.database_url.replace("+psycopg", "")
        sync_result = _sync_schema_contracts(dsn=dsn, records=records)
        summary.update(sync_result)
    else:
        summary["inserted_or_updated"] = 0
        summary["deprecated"] = 0

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "Schema contracts sync:"
        f" prepared={summary['contracts_prepared']}"
        f" upserted={summary['inserted_or_updated']}"
        f" deprecated={summary['deprecated']}"
        f" dry_run={summary['dry_run']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
