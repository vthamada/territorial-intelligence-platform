"""
Geocode polling places for a municipality using OSM POIs + Nominatim.

Usage:
    python -m scripts.geocode_polling_places [--municipality-code 3121605] [--dry-run]

Strategy:
1. Load polling places from dim_territory metadata (electoral sections)
2. Try matching against existing OSM education POIs in map.urban_poi
3. Fallback: query Nominatim API for each unmatched place
4. Update dim_territory geometry for all matched sections
"""
from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from typing import Any

import httpx
from sqlalchemy import text

# -- allow running as `python -m scripts.geocode_polling_places` from repo root
sys.path.insert(0, "src")

from app.db import session_scope  # noqa: E402
from app.logging import get_logger  # noqa: E402

logger = get_logger("geocode_polling_places")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_DELAY = 1.1  # seconds between requests (respect usage policy)
USER_AGENT = "territorial-intelligence-platform/1.0 (geocode-polling-places)"


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def _normalize(value: str) -> str:
    """Remove accents, uppercase, strip common school prefixes."""
    if not value:
        return ""
    s = unicodedata.normalize("NFD", value)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.upper().strip()
    return s


def _normalize_school_name(value: str) -> str:
    """Aggressive normalization for school-name matching."""
    s = _normalize(value)
    # Remove common prefixes
    s = re.sub(
        r"^(ESCOLA\s+(ESTADUAL|MUNICIPAL)\s+(DE\s+ED\.?\s*(UCACAO)?\s+INFANTIL\s+)?|"
        r"E\.\s*E\.\s*|E\.\s*M\.\s*(DE\s+ED\.?\s+INFANTIL\s+)?|"
        r"CMEI\s+|PROF\.?\s*[ªA]?\s*)",
        "",
        s,
    )
    # Remove parenthetical suffixes
    s = re.sub(r"\s*\(.*\)\s*$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# Step 1: Load polling places from DB
# ---------------------------------------------------------------------------

def _load_polling_places(session: Any, municipality_ibge_code: str) -> list[dict]:
    """Return unique polling places with section count and voters."""
    rows = session.execute(
        text("""
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
            ORDER BY total_voters DESC
        """),
        {"muni": municipality_ibge_code},
    ).fetchall()
    return [
        {
            "code": r[0],
            "name": r[1],
            "sections": r[2],
            "voters": r[3],
            "lat": None,
            "lon": None,
            "source": None,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Step 2: Match against existing OSM POIs
# ---------------------------------------------------------------------------

def _match_osm_pois(
    session: Any,
    polling_places: list[dict],
    municipality_center: tuple[float, float],
    search_radius_m: int = 30_000,
) -> int:
    """Try to match polling places against OSM POIs by normalized name.
    Returns count of matched items.
    """
    lon, lat = municipality_center
    pois = session.execute(
        text("""
            SELECT name, subcategory,
                   ST_X(geom::geometry) AS lon, ST_Y(geom::geometry) AS lat
            FROM map.urban_poi 
            WHERE ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius
            )
            AND name IS NOT NULL
        """),
        {"lon": lon, "lat": lat, "radius": search_radius_m},
    ).fetchall()

    # Build index: normalized name -> (original_name, lon, lat)
    poi_idx: dict[str, tuple[str, float, float]] = {}
    for p in pois:
        key = _normalize_school_name(p[0])
        if key:
            poi_idx[key] = (p[0], p[2], p[3])
        # Also index the plain normalized name
        key2 = _normalize(p[0])
        if key2 and key2 not in poi_idx:
            poi_idx[key2] = (p[0], p[2], p[3])

    matched = 0
    for pp in polling_places:
        if pp["lat"] is not None:
            continue
        pp_key = _normalize_school_name(pp["name"])
        # Exact match
        if pp_key in poi_idx:
            poi = poi_idx[pp_key]
            pp["lon"], pp["lat"] = poi[1], poi[2]
            pp["source"] = f"osm_poi:{poi[0]}"
            matched += 1
            continue
        # Substring match (only if substring is long enough)
        if len(pp_key) >= 6:
            for key, poi in poi_idx.items():
                if len(key) >= 6 and (pp_key in key or key in pp_key):
                    pp["lon"], pp["lat"] = poi[1], poi[2]
                    pp["source"] = f"osm_poi_partial:{poi[0]}"
                    matched += 1
                    break
    return matched


# ---------------------------------------------------------------------------
# Step 3: Nominatim geocoding fallback
# ---------------------------------------------------------------------------

def _geocode_nominatim(
    polling_places: list[dict],
    municipality_name: str,
    uf: str,
) -> int:
    """Query Nominatim for unmatched polling places. Returns count of newly matched."""
    unmatched = [pp for pp in polling_places if pp["lat"] is None]
    if not unmatched:
        return 0

    matched = 0
    client = httpx.Client(
        timeout=15.0,
        headers={"User-Agent": USER_AGENT},
    )

    for pp in unmatched:
        name = pp["name"]
        # Build search queries in order of specificity
        queries = [
            f"{name}, {municipality_name}, {uf}, Brasil",
            f"{name}, {municipality_name}, Minas Gerais, Brasil",
        ]
        # For schools, also try with expanded prefix
        expanded = _expand_school_prefix(name)
        if expanded != name:
            queries.insert(0, f"{expanded}, {municipality_name}, {uf}, Brasil")

        for q in queries:
            try:
                resp = client.get(
                    NOMINATIM_URL,
                    params={
                        "q": q,
                        "format": "json",
                        "limit": 1,
                        "countrycodes": "br",
                    },
                )
                time.sleep(NOMINATIM_DELAY)

                if resp.status_code != 200:
                    logger.warning("Nominatim %d for '%s'", resp.status_code, q)
                    continue

                results = resp.json()
                if results:
                    r = results[0]
                    lat, lon = float(r["lat"]), float(r["lon"])
                    # Sanity: must be within ~50km of Diamantina center
                    if abs(lat - (-18.24)) < 0.5 and abs(lon - (-43.61)) < 0.5:
                        pp["lat"], pp["lon"] = lat, lon
                        pp["source"] = f"nominatim:{q}"
                        matched += 1
                        logger.info("Nominatim OK: %s -> (%.6f, %.6f)", name, lon, lat)
                        break
                    else:
                        logger.warning(
                            "Nominatim result too far: %s -> (%.6f, %.6f)", q, lon, lat
                        )
            except Exception as exc:
                logger.warning("Nominatim error for '%s': %s", q, exc)
                time.sleep(NOMINATIM_DELAY)

    client.close()
    return matched


def _expand_school_prefix(name: str) -> str:
    """Expand abbreviated school prefixes for better Nominatim results."""
    replacements = [
        (r"^E\.\s*E\.\s*", "Escola Estadual "),
        (r"^E\.\s*M\.\s*DE\s+ED\.?\s+INFANTIL\s+", "Escola Municipal de Educação Infantil "),
        (r"^E\.\s*M\.\s*", "Escola Municipal "),
        (r"^CMEI\s+", "Centro Municipal de Educação Infantil "),
    ]
    for pattern, repl in replacements:
        result = re.sub(pattern, repl, name, flags=re.IGNORECASE)
        if result != name:
            return result.strip()
    return name


# ---------------------------------------------------------------------------
# Step 4: Update DB
# ---------------------------------------------------------------------------

def _update_geometry(
    session: Any,
    polling_places: list[dict],
    municipality_ibge_code: str,
    dry_run: bool = False,
) -> int:
    """Update dim_territory geometry + metadata for geocoded polling places."""
    updated = 0
    for pp in polling_places:
        if pp["lat"] is None or pp["lon"] is None:
            continue

        if dry_run:
            logger.info(
                "[DRY RUN] Would update %s (%s) -> (%.6f, %.6f) [%s]",
                pp["name"], pp["code"], pp["lon"], pp["lat"], pp["source"],
            )
            updated += 1
            continue

        # Update all sections belonging to this polling place
        result = session.execute(
            text("""
                UPDATE silver.dim_territory
                SET geometry = ST_SetSRID(ST_MakePoint(:lon, :lat), 4674),
                    metadata = metadata || jsonb_build_object(
                        'geocode_source', :source,
                        'geocode_lon', :lon,
                        'geocode_lat', :lat
                    ),
                    updated_at = NOW()
                WHERE level = 'electoral_section'
                  AND municipality_ibge_code = :muni
                  AND metadata->>'polling_place_code' = :pp_code
            """),
            {
                "lon": pp["lon"],
                "lat": pp["lat"],
                "source": pp["source"],
                "muni": municipality_ibge_code,
                "pp_code": pp["code"],
            },
        )
        updated += result.rowcount
        logger.info(
            "Updated %d sections for %s -> (%.6f, %.6f) [%s]",
            result.rowcount, pp["name"], pp["lon"], pp["lat"], pp["source"],
        )
    return updated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(
    municipality_ibge_code: str = "3121605",
    municipality_name: str = "Diamantina",
    uf: str = "MG",
    center: tuple[float, float] = (-43.61, -18.24),
    dry_run: bool = False,
) -> dict[str, Any]:
    """Geocode all polling places for a municipality."""
    logger.info("Starting geocoding for %s (%s)", municipality_name, municipality_ibge_code)

    with session_scope() as session:
        # Step 1: Load polling places
        polling_places = _load_polling_places(session, municipality_ibge_code)
        logger.info("Loaded %d polling places", len(polling_places))

        if not polling_places:
            return {"status": "no_data", "total": 0}

        # Step 2: Match OSM POIs
        osm_matched = _match_osm_pois(session, polling_places, center)
        logger.info("OSM POI matched: %d/%d", osm_matched, len(polling_places))

        # Step 3: Nominatim fallback
        nominatim_matched = _geocode_nominatim(
            polling_places, municipality_name, uf
        )
        logger.info("Nominatim matched: %d additional", nominatim_matched)

        total_matched = sum(1 for pp in polling_places if pp["lat"] is not None)
        total_unmatched = len(polling_places) - total_matched
        logger.info(
            "Total matched: %d/%d (unmatched: %d)",
            total_matched, len(polling_places), total_unmatched,
        )

        # Step 4: Update DB
        sections_updated = _update_geometry(
            session, polling_places, municipality_ibge_code, dry_run=dry_run
        )

        # Report
        result = {
            "status": "ok",
            "total_polling_places": len(polling_places),
            "osm_matched": osm_matched,
            "nominatim_matched": nominatim_matched,
            "total_matched": total_matched,
            "total_unmatched": total_unmatched,
            "sections_updated": sections_updated,
            "dry_run": dry_run,
            "unmatched": [
                {"code": pp["code"], "name": pp["name"]}
                for pp in polling_places
                if pp["lat"] is None
            ],
            "matched": [
                {
                    "code": pp["code"],
                    "name": pp["name"],
                    "lon": pp["lon"],
                    "lat": pp["lat"],
                    "source": pp["source"],
                }
                for pp in polling_places
                if pp["lat"] is not None
            ],
        }

        for pp in result["unmatched"]:
            logger.warning("UNMATCHED: %s (%s)", pp["name"], pp["code"])

        return result


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    muni_code = "3121605"
    for arg in sys.argv[1:]:
        if arg.startswith("--municipality-code="):
            muni_code = arg.split("=", 1)[1]

    result = run(municipality_ibge_code=muni_code, dry_run=dry)
    print(json.dumps(result, indent=2, ensure_ascii=False))
