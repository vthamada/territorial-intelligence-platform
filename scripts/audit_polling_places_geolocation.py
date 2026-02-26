from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, "src")

from app.db import session_scope
from sqlalchemy import text


SQL = """
with section_rows as (
  select
    metadata->>'polling_place_code' as code,
    metadata->>'polling_place_name' as name,
    territory_id::text as territory_id,
    geometry as geom,
    metadata->>'geocode_source' as source,
    updated_at,
    coalesce((metadata->>'voters_section')::int, 0) as voters_section
  from silver.dim_territory
  where level = 'electoral_section'
    and municipality_ibge_code = :municipality
    and metadata->>'polling_place_code' is not null
),
polling_places as (
  select
    code,
    name,
    count(*) as sections,
    sum(voters_section) as voters
  from section_rows
  group by 1, 2
),
representative as (
  select code, name, geom, source
  from (
    select
      code,
      name,
      geom,
      source,
      row_number() over (
        partition by code, name
        order by updated_at desc nulls last, territory_id
      ) as rn
    from section_rows
  ) ranked
  where rn = 1
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
  r.source,
  p.sections,
  p.voters,
  st_y(r.geom) as lat,
  st_x(r.geom) as lon,
  d.name as district_name,
  d.territory_id::text as district_id,
  (d.territory_id is not null) as within_district
from polling_places p
join representative r on r.code = p.code and r.name = p.name
left join lateral (
  select d.*
  from districts d
  where st_contains(d.geometry, r.geom)
  order by st_area(d.geometry) asc
  limit 1
) d on true
order by p.code;
"""


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def _load_overrides(path: str) -> dict[str, dict[str, str]]:
    if not path:
        return {}
    csv_path = Path(path)
    if not csv_path.exists():
        return {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        out: dict[str, dict[str, str]] = {}
        for row in reader:
            code = (row.get("polling_place_code") or "").strip()
            if not code:
                continue
            out[code] = {
                "expected_district": (row.get("expected_district") or "").strip(),
                "latitude": (row.get("latitude") or "").strip(),
                "longitude": (row.get("longitude") or "").strip(),
            }
    return out


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
    parser.add_argument(
        "--overrides-csv",
        default="data/seed/polling_places_overrides_diamantina.csv",
        help="Optional override CSV with expected_district/coordinates.",
    )
    parser.add_argument(
        "--override-max-distance-m",
        type=float,
        default=1_500.0,
        help="Maximum allowed distance in meters from override coordinates.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    overrides = _load_overrides(args.overrides_csv)

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
    outside_any_district = [r["code"] for r in records if not r["within_district"]]
    outside_expected_district: list[str] = []
    override_distance_violations: list[str] = []

    for rec in records:
        code = str(rec["code"])
        override = overrides.get(code)
        if override is None:
            continue
        expected_district = override.get("expected_district") or None
        if expected_district and rec.get("district") != expected_district:
            outside_expected_district.append(code)
        override_lat = override.get("latitude") or ""
        override_lon = override.get("longitude") or ""
        if not override_lat or not override_lon:
            continue
        actual_lat = float(rec["lat"])
        actual_lon = float(rec["lon"])
        dist_m = _haversine_m(actual_lat, actual_lon, float(override_lat), float(override_lon))
        rec["override_distance_m"] = round(dist_m, 1)
        rec["override_match"] = dist_m <= float(args.override_max_distance_m)
        if dist_m > float(args.override_max_distance_m):
            override_distance_violations.append(code)

    has_violations = bool(
        outside_any_district
        or outside_expected_district
        or override_distance_violations
    )

    report = {
        "municipality": args.municipality,
        "polling_places_total": len(records),
        "unique_codes": len({r["code"] for r in records}),
        "unique_points": len(unique_points),
        "outside_any_district": outside_any_district,
        "outside_expected_district": sorted(set(outside_expected_district)),
        "override_distance_violations": sorted(set(override_distance_violations)),
        "status": "pass" if len(records) > 0 and not has_violations else "warn",
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
                "outside_any_district": report["outside_any_district"],
                "outside_expected_district": report["outside_expected_district"],
                "override_distance_violations": report["override_distance_violations"],
                "status": report["status"],
            },
            ensure_ascii=False,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
