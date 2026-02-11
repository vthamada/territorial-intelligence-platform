from __future__ import annotations

import argparse
import sys
from pathlib import Path

import sqlalchemy as sa

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    src_str = str(SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

from app.settings import get_settings  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Remove legacy *_SOURCE_PROBE indicators from silver.fact_indicator. "
            "Use --apply to execute deletion; default mode is dry-run."
        )
    )
    parser.add_argument(
        "--sources",
        nargs="*",
        default=["INEP", "DATASUS", "SICONFI", "MTE"],
        help="Source list to target (default: INEP DATASUS SICONFI MTE).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply deletion. Without this flag, script only reports what would be deleted.",
    )
    return parser


def _fetch_probe_rows(conn: sa.Connection, sources: list[str]) -> list[tuple[str, str, int]]:
    rows = conn.execute(
        sa.text(
            """
            SELECT source, reference_period, COUNT(*) AS count
            FROM silver.fact_indicator
            WHERE indicator_code LIKE '%_SOURCE_PROBE'
              AND source = ANY(:sources)
            GROUP BY source, reference_period
            ORDER BY source, reference_period
            """
        ),
        {"sources": sources},
    ).fetchall()
    return [(str(row[0]), str(row[1]), int(row[2])) for row in rows]


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = get_settings()
    engine = sa.create_engine(settings.database_url)

    with engine.begin() as conn:
        before = _fetch_probe_rows(conn, args.sources)
        total_before = sum(row[2] for row in before)
        print(f"Legacy SOURCE_PROBE rows found: {total_before}")
        for source, reference_period, count in before:
            print(f" - {source} | {reference_period} | {count}")

        if not args.apply:
            print("Dry-run mode: no rows deleted. Re-run with --apply to execute.")
            return 0

        conn.execute(
            sa.text(
                """
                DELETE FROM silver.fact_indicator
                WHERE indicator_code LIKE '%_SOURCE_PROBE'
                  AND source = ANY(:sources)
                """
            ),
            {"sources": args.sources},
        )

        after = _fetch_probe_rows(conn, args.sources)
        total_after = sum(row[2] for row in after)
        deleted = total_before - total_after
        print(f"Deleted rows: {deleted}")
        print(f"Remaining SOURCE_PROBE rows for selected sources: {total_after}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
