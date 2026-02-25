"""
Apply seed CSV coordinates to dim_territory in the database.
Reads data/seed/polling_places_diamantina.csv and updates geometry for each polling place.
"""
from __future__ import annotations
import csv, sys
sys.path.insert(0, "src")

def main():
    from app.db import session_scope
    from sqlalchemy import text

    seed_path = "data/seed/polling_places_diamantina.csv"
    print(f"Reading seed: {seed_path}")

    entries = []
    with open(seed_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["latitude"] and row["longitude"]:
                entries.append(row)

    print(f"  {len(entries)} places with coordinates")

    total_sections = 0
    with session_scope() as session:
        for e in entries:
            code = e["polling_place_code"]
            name = e["polling_place_name"]
            lat = float(e["latitude"])
            lon = float(e["longitude"])
            source = e["source"]

            result = session.execute(
                text("""
                    UPDATE silver.dim_territory
                    SET geometry = ST_SetSRID(ST_MakePoint(CAST(:lon AS float), CAST(:lat AS float)), 4674),
                        metadata = metadata || jsonb_build_object(
                            'geocode_source', CAST(:source AS text),
                            'geocode_lon', CAST(:lon AS float),
                            'geocode_lat', CAST(:lat AS float)
                        ),
                        updated_at = NOW()
                    WHERE level = 'electoral_section'
                      AND municipality_ibge_code = '3121605'
                      AND metadata->>'polling_place_code' = :pp_code
                """),
                {"lon": lon, "lat": lat, "source": source, "pp_code": code},
            )
            total_sections += result.rowcount
            print(f"  {name} ({code}): {result.rowcount} sections -> ({lat:.6f}, {lon:.6f}) [{source}]")

    print(f"\nTotal sections updated: {total_sections}")

    # Verify
    with session_scope() as session:
        check = session.execute(
            text("""
                SELECT 
                    COUNT(DISTINCT ST_AsText(geometry)) AS unique_points,
                    COUNT(*) AS total_sections
                FROM silver.dim_territory
                WHERE level = 'electoral_section'
                  AND municipality_ibge_code = '3121605'
            """),
        ).fetchone()
        print(f"Verification: {check[0]} unique geometry points for {check[1]} sections")

if __name__ == "__main__":
    main()
