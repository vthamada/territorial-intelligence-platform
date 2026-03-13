from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.db import session_scope
from app.settings import get_settings
from pipelines.tse_party_registry import build_party_lookup, enrich_candidate_row_party


def _load_candidate_rows() -> list[dict[str, Any]]:
    settings = get_settings()
    with session_scope(settings) as session:
        rows = session.execute(
            text(
                """
                SELECT
                    dc.candidate_id::text AS candidate_id,
                    de.election_year,
                    de.office,
                    dc.candidate_number,
                    dc.candidate_name,
                    dc.ballot_name,
                    dc.party_abbr,
                    dc.party_number,
                    dc.party_name
                FROM silver.dim_candidate dc
                JOIN silver.dim_election de
                  ON de.election_id = dc.election_id
                ORDER BY de.election_year, de.office, dc.candidate_number, dc.candidate_name
                """
            )
        ).mappings()
        return [dict(row) for row in rows]


def backfill_candidate_party_identity(*, apply: bool, output_path: Path | None) -> dict[str, Any]:
    settings = get_settings()
    rows = _load_candidate_rows()
    lookup = build_party_lookup(rows)

    updated_rows: list[dict[str, Any]] = []
    for row in rows:
        original = {
            "party_abbr": row.get("party_abbr"),
            "party_number": row.get("party_number"),
            "party_name": row.get("party_name"),
        }
        enrich_candidate_row_party(row, party_lookup=lookup)
        if (
            original["party_abbr"] != row.get("party_abbr")
            or original["party_number"] != row.get("party_number")
            or original["party_name"] != row.get("party_name")
        ):
            updated_rows.append(
                {
                    "candidate_id": row["candidate_id"],
                    "party_abbr": row.get("party_abbr"),
                    "party_number": row.get("party_number"),
                    "party_name": row.get("party_name"),
                }
            )

    updated_count = 0
    if apply and updated_rows:
        with session_scope(settings) as session:
            for row in updated_rows:
                session.execute(
                    text(
                        """
                        UPDATE silver.dim_candidate
                        SET
                            party_abbr = COALESCE(:party_abbr, party_abbr),
                            party_number = COALESCE(:party_number, party_number),
                            party_name = COALESCE(:party_name, party_name),
                            metadata = COALESCE(metadata, '{}'::jsonb) || CAST(:metadata AS jsonb),
                            updated_at = NOW()
                        WHERE candidate_id = CAST(:candidate_id AS uuid)
                        """
                    ),
                    {
                        "candidate_id": row["candidate_id"],
                        "party_abbr": row["party_abbr"],
                        "party_number": row["party_number"],
                        "party_name": row["party_name"],
                        "metadata": json.dumps(
                            {
                                "party_enrichment_method": "candidate_number_prefix",
                                "party_enrichment_updated_at": datetime.now(UTC).isoformat(),
                            }
                        ),
                    },
                )
        updated_count = len(updated_rows)

    report = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "apply": apply,
        "rows_scanned": len(rows),
        "party_lookup_pairs": len(lookup),
        "candidates_enriched": len(updated_rows),
        "rows_updated": updated_count,
        "preview": updated_rows[:25],
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill party identity in silver.dim_candidate using legend rows and candidate number prefix."
    )
    parser.add_argument("--apply", action="store_true", help="Persist updates to the database.")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional JSON report path.",
    )
    args = parser.parse_args()
    report = backfill_candidate_party_identity(apply=args.apply, output_path=args.output_json)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
