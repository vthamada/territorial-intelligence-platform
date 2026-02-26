from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from app.db import session_scope
from sqlalchemy import text


SQL = """
with polling_places as (
  select
    metadata->>'polling_place_code' as code,
    metadata->>'polling_place_name' as name,
    max(geometry) as geom,
    max(metadata->>'geocode_source') as source,
    count(*) as sections,
    sum(coalesce((metadata->>'voters_section')::int, 0)) as voters
  from silver.dim_territory
  where level = 'electoral_section'
    and municipality_ibge_code = :municipality
    and metadata->>'polling_place_code' is not null
  group by 1, 2
),
districts as (
  select territory_id, name, geometry
  from silver.dim_territory
  where level = 'district'
    and municipality_ibge_code = :municipality
)
select
  p.code,
  p.name,
  p.source,
  p.sections,
  p.voters,
  st_y(p.geom) as lat,
  st_x(p.geom) as lon,
  d.name as district_name,
  st_within(p.geom, d.geometry) as within_district
from polling_places p
join districts d on st_contains(d.geometry, p.geom)
order by p.code;
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit polling-place geolocation consistency by district.",
    )
    parser.add_argument(
        "--municipality",
        default="3121605",
        help="IBGE municipality code (default: 3121605).",
    )
    parser.add_argument(
        "--output-json",
        default="data/reports/polling_places_geolocation_audit.json",
        help="Path to write JSON report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)

    with session_scope() as session:
        rows = session.execute(text(SQL), {"municipality": args.municipality}).fetchall()

    records: list[dict[str, object]] = []
    for row in rows:
        records.append(
            {
                "code": row.code,
                "name": row.name,
                "district": row.district_name,
                "source": row.source,
                "sections": int(row.sections),
                "voters": int(row.voters),
                "lat": round(float(row.lat), 6),
                "lon": round(float(row.lon), 6),
                "within_district": bool(row.within_district),
            }
        )

    unique_points = {(r["lat"], r["lon"]) for r in records}
    outside = [r["code"] for r in records if not r["within_district"]]

    report = {
        "municipality": args.municipality,
        "polling_places_total": len(records),
        "unique_codes": len({r["code"] for r in records}),
        "unique_points": len(unique_points),
        "outside_district": outside,
        "status": "pass" if len(records) > 0 and not outside else "warn",
        "items": records,
    }

    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Audit written to: {output}")
    print(
        "Summary:",
        json.dumps(
            {
                "polling_places_total": report["polling_places_total"],
                "unique_points": report["unique_points"],
                "outside_district": report["outside_district"],
                "status": report["status"],
            },
            ensure_ascii=False,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
