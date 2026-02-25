"""
Geocode polling places using INEP Censo Escolar addresses + Nominatim.

Strategy:
1. Download INEP microdata (has school addresses but no lat/lon since 2024)
2. Match INEP schools to TSE polling places by normalized name
3. Geocode addresses via Nominatim (street + number + neighborhood)
4. For non-school places, try direct Nominatim queries
5. Save seed CSV and update DB

Usage:
    python scripts/geocode_with_addresses.py [--dry-run] [--save-seed]
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import time
import unicodedata
import zipfile
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

# Allow running from repo root
sys.path.insert(0, "src")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_DELAY = 1.1
USER_AGENT = "territorial-intelligence-platform/1.0 (geocode-polling-places)"
INEP_URL = "https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_2024.zip"
DIAMANTINA_CENTER = (-18.2337, -43.6021)  # lat, lon
MUNICIPALITY_CODE = 3121605
MAX_DIST_KM = 50  # reject geocoding results farther than this


def _normalize(value: str) -> str:
    """Remove accents, uppercase, strip."""
    if not value:
        return ""
    s = unicodedata.normalize("NFD", value)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.upper().strip()


def _strip_prefixes(s: str) -> str:
    """Remove common school prefixes for matching."""
    s = re.sub(
        r"^(ESCOLA\s+(ESTADUAL|MUNICIPAL)\s+(DE\s+EDUCA[CÇ]AO\s+INFANTIL\s+)?|"
        r"E\.\s*E\.\s*|E\.\s*M\.\s*(DE\s+ED\.?\s*U?CA[CÇ]AO\s+INFANTIL\s+)?|"
        r"EE\s+|EM\s+|"
        r"CMEI\s+|"
        r"CENTRO\s+MUNICIPAL\s+DE\s+EDUCA[CÇ]AO\s+INFANTIL\s+|"
        r"PROF\.?\s*[ªA]?\s*|PROFESSOR[A]?\s*)",
        "",
        s,
    )
    s = re.sub(r"\s*\(.*\)\s*$", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _match_score(tse_name: str, inep_name: str) -> float:
    """Score 0-1 for how well names match."""
    tn = _strip_prefixes(_normalize(tse_name))
    ine = _strip_prefixes(_normalize(inep_name))
    if not tn or not ine:
        return 0.0
    if tn == ine:
        return 1.0
    # One contains the other
    if tn in ine or ine in tn:
        shorter = min(len(tn), len(ine))
        longer = max(len(tn), len(ine))
        return shorter / longer
    # Word overlap
    tw = set(tn.split())
    iw = set(ine.split())
    if not tw or not iw:
        return 0.0
    overlap = tw & iw
    return len(overlap) / max(len(tw), len(iw))


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in km between two points."""
    import math
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Step 1: Download INEP data and extract Diamantina schools
# ---------------------------------------------------------------------------

def download_inep_schools(cache_path: str = "data/inep_diamantina_schools.csv") -> pd.DataFrame:
    """Download INEP microdata, extract schools for Diamantina.
    Caches result as CSV to avoid re-downloading."""
    if os.path.exists(cache_path):
        print(f"  Using cached INEP data: {cache_path}")
        return pd.read_csv(cache_path, sep=";", encoding="utf-8")

    print(f"  Downloading INEP microdata from {INEP_URL}...")
    client = httpx.Client(timeout=300, follow_redirects=True,
                          headers={"User-Agent": USER_AGENT})
    resp = client.get(INEP_URL)
    client.close()
    print(f"  Downloaded {len(resp.content) / 1024 / 1024:.1f} MB")

    print("  Extracting school data...")
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    # Find the main schools CSV
    csv_files = [n for n in zf.namelist() if n.endswith(".csv") and "suplemento" not in n.lower()]
    if not csv_files:
        raise RuntimeError("No school CSV found in INEP ZIP")

    csv_name = csv_files[0]
    print(f"  Reading {csv_name}...")
    with zf.open(csv_name) as f:
        df = pd.read_csv(f, sep=";", encoding="latin1", low_memory=False)

    # Filter Diamantina
    df_muni = df[df["CO_MUNICIPIO"] == MUNICIPALITY_CODE].copy()
    print(f"  Found {len(df_muni)} schools in Diamantina")

    # Keep relevant columns
    keep_cols = [
        "CO_ENTIDADE", "NO_ENTIDADE", "CO_MUNICIPIO", "NO_MUNICIPIO",
        "DS_ENDERECO", "NU_ENDERECO", "DS_COMPLEMENTO", "NO_BAIRRO", "CO_CEP",
        "TP_SITUACAO_FUNCIONAMENTO", "TP_DEPENDENCIA",
    ]
    available = [c for c in keep_cols if c in df_muni.columns]
    df_out = df_muni[available].copy()

    # Save cache
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    df_out.to_csv(cache_path, sep=";", index=False, encoding="utf-8")
    print(f"  Cached to {cache_path}")
    return df_out


# ---------------------------------------------------------------------------
# Step 2: Load polling places from DB
# ---------------------------------------------------------------------------

def load_polling_places_from_db() -> list[dict]:
    """Load unique polling places from dim_territory."""
    from app.db import session_scope
    with session_scope() as session:
        from sqlalchemy import text
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
            {"muni": str(MUNICIPALITY_CODE)},
        ).fetchall()
    return [
        {"code": r[0], "name": r[1], "sections": int(r[2]), "voters": int(r[3]),
         "lat": None, "lon": None, "source": None, "address": None}
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Step 3: Match INEP schools to polling places
# ---------------------------------------------------------------------------

def match_inep_to_polling_places(
    inep_df: pd.DataFrame,
    polling_places: list[dict],
) -> dict[str, dict]:
    """Match polling places to INEP schools, return {pp_code: inep_row}."""
    matches = {}

    for pp in polling_places:
        best_score = 0.0
        best_row = None

        for _, row in inep_df.iterrows():
            inep_name = str(row.get("NO_ENTIDADE", ""))
            score = _match_score(pp["name"], inep_name)

            if score > best_score:
                best_score = score
                best_row = row

        if best_score >= 0.5 and best_row is not None:
            addr = str(best_row.get("DS_ENDERECO", ""))
            num = str(best_row.get("NU_ENDERECO", ""))
            bairro = str(best_row.get("NO_BAIRRO", ""))

            if num and num not in ("nan", "0", "S/N", "SN"):
                addr = f"{addr}, {num}"

            matches[pp["code"]] = {
                "inep_name": str(best_row.get("NO_ENTIDADE", "")),
                "address": addr,
                "neighborhood": bairro if bairro != "nan" else "",
                "cep": str(best_row.get("CO_CEP", "")),
                "score": best_score,
            }
            pp["address"] = addr
            print(f"  INEP match: {pp['name']} -> {best_row.get('NO_ENTIDADE')} "
                  f"(score: {best_score:.2f}) @ {addr}, {bairro}")
        else:
            print(f"  No INEP match for: {pp['name']} (best: {best_score:.2f})")

    return matches


# ---------------------------------------------------------------------------
# Step 4: Geocode via Nominatim using addresses
# ---------------------------------------------------------------------------

def geocode_all(
    polling_places: list[dict],
    inep_matches: dict[str, dict],
) -> int:
    """Geocode polling places using INEP addresses + Nominatim.
    Returns count of successfully geocoded places."""
    client = httpx.Client(
        timeout=15.0,
        headers={"User-Agent": USER_AGENT},
    )
    geocoded = 0

    for pp in polling_places:
        if pp["lat"] is not None:
            continue

        name = pp["name"]
        queries = []

        # If we have INEP address, use that first (best accuracy)
        if pp["code"] in inep_matches:
            m = inep_matches[pp["code"]]
            addr = m["address"]
            bairro = m["neighborhood"]

            # Address queries (more specific first)
            if bairro:
                queries.append(f"{addr}, {bairro}, Diamantina, MG, Brasil")
            queries.append(f"{addr}, Diamantina, MG, Brasil")

        # Also try school name queries
        expanded = _expand_prefix(name)
        if expanded != name:
            queries.append(f"{expanded}, Diamantina, MG, Brasil")
        queries.append(f"{name}, Diamantina, MG, Brasil")
        queries.append(f"{name}, Diamantina, Minas Gerais, Brasil")

        for q in queries:
            try:
                resp = client.get(
                    NOMINATIM_URL,
                    params={"q": q, "format": "json", "limit": 3, "countrycodes": "br"},
                )
                time.sleep(NOMINATIM_DELAY)

                if resp.status_code != 200:
                    continue

                results = resp.json()
                for r in results:
                    lat, lon = float(r["lat"]), float(r["lon"])
                    dist = _haversine_km(
                        lat, lon, DIAMANTINA_CENTER[0], DIAMANTINA_CENTER[1]
                    )
                    if dist <= MAX_DIST_KM:
                        pp["lat"] = lat
                        pp["lon"] = lon
                        pp["source"] = f"nominatim_addr:{q}"
                        geocoded += 1
                        print(f"  OK: {name} -> ({lat:.6f}, {lon:.6f}) dist={dist:.1f}km query='{q}'")
                        break
                if pp["lat"] is not None:
                    break

            except Exception as exc:
                print(f"  ERROR: {q}: {exc}")
                time.sleep(NOMINATIM_DELAY)

        if pp["lat"] is None:
            print(f"  FAILED: {name}")

    client.close()
    return geocoded


def _expand_prefix(name: str) -> str:
    """Expand abbreviated school prefixes."""
    for pat, repl in [
        (r"^E\.\s*E\.\s*", "Escola Estadual "),
        (r"^E\.\s*M\.\s*DE\s+ED\.?\s+INFANTIL\s+", "Escola Municipal de Educação Infantil "),
        (r"^E\.\s*M\.\s*", "Escola Municipal "),
        (r"^CMEI\s+", "Centro Municipal de Educação Infantil "),
    ]:
        result = re.sub(pat, repl, name, flags=re.IGNORECASE)
        if result != name:
            return result.strip()
    return name


# ---------------------------------------------------------------------------
# Step 5: Save seed CSV
# ---------------------------------------------------------------------------

def save_seed_csv(polling_places: list[dict], path: str = "data/seed/polling_places_diamantina.csv"):
    """Save geocoded results as seed CSV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["polling_place_code", "polling_place_name", "latitude", "longitude",
                     "source", "sections", "voters"])
        for pp in polling_places:
            w.writerow([
                pp["code"], pp["name"],
                pp["lat"] or "", pp["lon"] or "",
                pp["source"] or "unmatched",
                pp["sections"], pp["voters"],
            ])
    print(f"\nSeed CSV saved: {path}")


# ---------------------------------------------------------------------------
# Step 6: Update DB
# ---------------------------------------------------------------------------

def update_db(polling_places: list[dict], dry_run: bool = False) -> int:
    """Update dim_territory geometry for geocoded polling places."""
    from app.db import session_scope
    from sqlalchemy import text

    geocoded = [pp for pp in polling_places if pp["lat"] is not None]
    if not geocoded:
        print("No geocoded places to update")
        return 0

    if dry_run:
        print(f"\n[DRY RUN] Would update {len(geocoded)} polling places:")
        for pp in geocoded:
            print(f"  {pp['name']} ({pp['code']}) -> ({pp['lat']:.6f}, {pp['lon']:.6f}) [{pp['source']}]")
        return 0

    updated = 0
    with session_scope() as session:
        for pp in geocoded:
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
                    "lon": pp["lon"], "lat": pp["lat"],
                    "source": pp["source"],
                    "muni": str(MUNICIPALITY_CODE),
                    "pp_code": pp["code"],
                },
            )
            updated += result.rowcount
            print(f"  Updated {result.rowcount} sections for {pp['name']}")

    return updated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dry_run = "--dry-run" in sys.argv
    save_seed = "--save-seed" in sys.argv or True  # always save seed

    print("=" * 60)
    print("Geocoding Polling Places - Diamantina (3121605)")
    print("=" * 60)

    # Step 1: INEP data
    print("\n[1/6] Loading INEP school data...")
    inep_df = download_inep_schools()
    print(f"  {len(inep_df)} schools loaded")

    # Step 2: Polling places
    print("\n[2/6] Loading polling places from DB...")
    polling_places = load_polling_places_from_db()
    print(f"  {len(polling_places)} polling places loaded")

    # Step 3: Match INEP to polling places
    print("\n[3/6] Matching INEP schools to polling places...")
    inep_matches = match_inep_to_polling_places(inep_df, polling_places)
    print(f"  {len(inep_matches)}/{len(polling_places)} matched to INEP schools")

    # Step 4: Geocode
    print("\n[4/6] Geocoding via Nominatim (address-based)...")
    geocoded = geocode_all(polling_places, inep_matches)
    total_ok = sum(1 for pp in polling_places if pp["lat"] is not None)
    total_fail = len(polling_places) - total_ok
    print(f"\n  Geocoded: {total_ok}/{len(polling_places)} ({total_fail} unmatched)")

    # Step 5: Save seed
    if save_seed:
        print("\n[5/6] Saving seed CSV...")
        save_seed_csv(polling_places)

    # Step 6: Update DB
    print(f"\n[6/6] Updating DB {'(DRY RUN)' if dry_run else ''}...")
    updated = update_db(polling_places, dry_run=dry_run)
    if not dry_run:
        print(f"  Updated {updated} sections in DB")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total polling places: {len(polling_places)}")
    print(f"INEP address matches: {len(inep_matches)}")
    print(f"Geocoded:             {total_ok}")
    print(f"Unmatched:            {total_fail}")
    if total_fail > 0:
        print("\nUnmatched places:")
        for pp in polling_places:
            if pp["lat"] is None:
                print(f"  - {pp['name']} ({pp['code']})")


if __name__ == "__main__":
    main()
