from __future__ import annotations

"""
Rebuild polling-place seed without mutating existing coordinates.

Behavior:
1. Reads the current `data/seed/polling_places_diamantina.csv` as the source of
   truth for latitude/longitude/source.
2. Recomputes `sections` and `voters` from `silver.dim_territory`.
3. Writes an updated CSV preserving coordinates.

This avoids regressions where old hardcoded coordinate dictionaries overwrite
manual/geocoded corrections.
"""

import csv
import os
import sys

sys.path.insert(0, "src")

SEED_PATH = "data/seed/polling_places_diamantina.csv"
OVERRIDES_PATH = "data/seed/polling_places_overrides_diamantina.csv"
MUNICIPALITY_CODE = "3121605"


def load_existing_seed(path: str) -> dict[str, dict[str, str]]:
    if not os.path.exists(path):
        return {}

    by_code: dict[str, dict[str, str]] = {}
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("polling_place_code") or "").strip()
            if not code:
                continue
            by_code[code] = {
                "name": (row.get("polling_place_name") or "").strip(),
                "latitude": (row.get("latitude") or "").strip(),
                "longitude": (row.get("longitude") or "").strip(),
                "source": (row.get("source") or "seed").strip() or "seed",
            }
    return by_code


def fetch_polling_places_from_db() -> list[tuple[str, str, int, int]]:
    from app.db import session_scope
    from sqlalchemy import text

    sql = text(
        """
        SELECT
          metadata->>'polling_place_code' AS code,
          metadata->>'polling_place_name' AS name,
          COUNT(*) AS sections,
          SUM(COALESCE((metadata->>'voters_section')::int, 0)) AS total_voters
        FROM silver.dim_territory
        WHERE level = 'electoral_section'
          AND municipality_ibge_code = :muni
          AND metadata->>'polling_place_code' IS NOT NULL
        GROUP BY 1, 2
        ORDER BY total_voters DESC, code
        """,
    )

    with session_scope() as session:
        rows = session.execute(sql, {"muni": MUNICIPALITY_CODE}).fetchall()

    return [(r[0], r[1], int(r[2]), int(r[3])) for r in rows]


def load_overrides(path: str) -> dict[str, dict[str, str]]:
    if not os.path.exists(path):
        return {}

    by_code: dict[str, dict[str, str]] = {}
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("polling_place_code") or "").strip()
            latitude = (row.get("latitude") or "").strip()
            longitude = (row.get("longitude") or "").strip()
            source = (row.get("source") or "").strip()
            if not code or not latitude or not longitude:
                continue
            by_code[code] = {
                "latitude": latitude,
                "longitude": longitude,
                "source": source or "override",
            }
    return by_code


def write_seed(path: str, rows: list[list[object]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "polling_place_code",
                "polling_place_name",
                "latitude",
                "longitude",
                "source",
                "sections",
                "voters",
            ]
        )
        writer.writerows(rows)


def main() -> None:
    existing = load_existing_seed(SEED_PATH)
    overrides = load_overrides(OVERRIDES_PATH)
    db_rows = fetch_polling_places_from_db()

    out_rows: list[list[object]] = []
    missing_coords = 0
    overrides_applied = 0

    for code, name, sections, voters in db_rows:
        seed_entry = existing.get(code, {})
        latitude = seed_entry.get("latitude", "")
        longitude = seed_entry.get("longitude", "")
        source = seed_entry.get("source", "seed")

        override_entry = overrides.get(code)
        if override_entry is not None:
            override_lat = override_entry["latitude"]
            override_lon = override_entry["longitude"]
            override_source = override_entry["source"]
            if (
                latitude != override_lat
                or longitude != override_lon
                or source != override_source
            ):
                overrides_applied += 1
            latitude = override_lat
            longitude = override_lon
            source = override_source

        if not latitude or not longitude:
            missing_coords += 1

        out_rows.append([code, name, latitude, longitude, source, sections, voters])

    write_seed(SEED_PATH, out_rows)

    print(f"Seed rebuilt: {SEED_PATH}")
    print(f"Rows: {len(out_rows)}")
    print(f"Rows missing coordinates: {missing_coords}")
    print(f"Overrides loaded: {len(overrides)}")
    print(f"Overrides applied: {overrides_applied}")


if __name__ == "__main__":
    main()
