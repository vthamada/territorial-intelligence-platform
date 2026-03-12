from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import psycopg

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from app.settings import get_settings  # noqa: E402


def _parse_years(raw: str | None) -> list[int] | None:
    if raw is None or not raw.strip():
        return None
    years: list[int] = []
    for chunk in raw.split(","):
        value = chunk.strip()
        if not value:
            continue
        years.append(int(value))
    return years or None


def _load_summary(conn: psycopg.Connection, years: list[int] | None) -> list[dict[str, int]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH section_years AS (
                SELECT DISTINCT de.election_year
                FROM silver.fact_candidate_vote fcv
                JOIN silver.dim_territory dt ON dt.territory_id = fcv.territory_id
                JOIN silver.dim_election de ON de.election_id = fcv.election_id
                WHERE dt.level::text = 'electoral_section'
                  AND (%(years)s::int[] IS NULL OR de.election_year = ANY(%(years)s::int[]))
            )
            SELECT
                de.election_year,
                COUNT(*)::int AS zone_rows,
                COUNT(DISTINCT fcv.territory_id)::int AS zone_territories,
                COUNT(DISTINCT fcv.candidate_id)::int AS candidates
            FROM silver.fact_candidate_vote fcv
            JOIN silver.dim_territory dt ON dt.territory_id = fcv.territory_id
            JOIN silver.dim_election de ON de.election_id = fcv.election_id
            WHERE dt.level::text = 'electoral_zone'
              AND de.election_year IN (SELECT election_year FROM section_years)
              AND (%(years)s::int[] IS NULL OR de.election_year = ANY(%(years)s::int[]))
            GROUP BY de.election_year
            ORDER BY de.election_year DESC
            """,
            {"years": years},
        )
        columns = [desc.name for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def _delete_legacy_rows(conn: psycopg.Connection, years: list[int] | None) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH section_years AS (
                SELECT DISTINCT de.election_year
                FROM silver.fact_candidate_vote fcv
                JOIN silver.dim_territory dt ON dt.territory_id = fcv.territory_id
                JOIN silver.dim_election de ON de.election_id = fcv.election_id
                WHERE dt.level::text = 'electoral_section'
                  AND (%(years)s::int[] IS NULL OR de.election_year = ANY(%(years)s::int[]))
            )
            DELETE FROM silver.fact_candidate_vote fcv
            USING silver.dim_territory dt, silver.dim_election de
            WHERE dt.territory_id = fcv.territory_id
              AND de.election_id = fcv.election_id
              AND dt.level::text = 'electoral_zone'
              AND de.election_year IN (SELECT election_year FROM section_years)
              AND (%(years)s::int[] IS NULL OR de.election_year = ANY(%(years)s::int[]))
            """,
            {"years": years},
        )
        return int(cur.rowcount or 0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove linhas legadas de fact_candidate_vote em electoral_zone quando o mesmo ano já possui carga em electoral_section."
    )
    parser.add_argument("--years", help="Anos separados por vírgula. Ex.: 2024,2022")
    parser.add_argument("--apply", action="store_true", help="Executa a limpeza. Sem a flag, roda apenas dry-run.")
    parser.add_argument("--output-json", help="Arquivo opcional para salvar o relatório.")
    args = parser.parse_args()

    settings = get_settings()
    years = _parse_years(args.years)
    dsn = settings.database_url.replace("+psycopg", "")

    report: dict[str, object] = {
        "status": "dry_run",
        "years": years,
        "summary_before": [],
        "deleted_rows": 0,
        "summary_after": [],
    }

    with psycopg.connect(dsn) as conn:
        report["summary_before"] = _load_summary(conn, years)
        if args.apply:
            deleted_rows = _delete_legacy_rows(conn, years)
            conn.commit()
            report["status"] = "applied"
            report["deleted_rows"] = deleted_rows
            report["summary_after"] = _load_summary(conn, years)
        else:
            conn.rollback()

    if args.output_json:
        output = Path(args.output_json)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
