"""
Build the final comprehensive seed CSV for all 36 polling places.
Combines Nominatim results + manual neighborhood/district estimates for remaining.
"""
from __future__ import annotations
import csv, json, os, sys
sys.path.insert(0, "src")

# ---- VERIFIED Nominatim results (from runs 1 and 2) ----
GEOCODED = {
    # Run 1 - Address-based, verified <5km from center
    "1210": {"lat": -18.246070, "lon": -43.599738, "source": "nominatim_addr:R NAZARE 233"},
    "1198": {"lat": -18.248018, "lon": -43.597017, "source": "nominatim_addr:R JOGO DA BOLA 120"},
    "1040": {"lat": -18.238212, "lon": -43.611947, "source": "nominatim_addr:R ENOLOGIA 303"},
    "1082": {"lat": -18.242277, "lon": -43.598272, "source": "nominatim_addr:R MACAU DE BAIXO 307"},
    "1058": {"lat": -18.241914, "lon": -43.598926, "source": "nominatim_addr:R MACAU DO MEIO 338"},
    "1368": {"lat": -18.246828, "lon": -43.598947, "source": "nominatim_addr:R DAS MERCES"},
    "1520": {"lat": -18.245545, "lon": -43.603104, "source": "nominatim:SRE Diamantina"},
    "1473": {"lat": -18.244310, "lon": -43.590590, "source": "nominatim_addr:R DAS CAMELIAS 311"},
    "1490": {"lat": -18.227639, "lon": -43.609694, "source": "nominatim_addr:RUA CONSUELO FALCI 231"},
    "1163": {"lat": -18.245334, "lon": -43.594527, "source": "nominatim:INSS Diamantina"},
    "1503": {"lat": -18.235873, "lon": -43.634538, "source": "nominatim_addr:RUA CASACA PARDA 231"},
    "1279": {"lat": -18.260997, "lon": -43.579841, "source": "nominatim_addr:RUA GRUTA DE LOURDES 4180"},

    # Run 2 - Targeted queries
    "1015": {"lat": -18.241002, "lon": -43.602567, "source": "nominatim:UEMG Diamantina"},
    "1228": {"lat": -18.253042, "lon": -43.590732, "source": "nominatim_addr:RUA CRUZ DE MOISES"},
    "1309": {"lat": -17.944828, "lon": -43.623091, "source": "nominatim:Inhai district"},
    "1252": {"lat": -18.288146, "lon": -43.982384, "source": "nominatim:Conselheiro Mata"},
    "1341": {"lat": -18.216500, "lon": -43.906394, "source": "nominatim:Conselheiro Mata"},
    "1376": {"lat": -18.181579, "lon": -43.694889, "source": "nominatim:Distrito Sopa"},
    "1295": {"lat": -18.281855, "lon": -43.728092, "source": "nominatim:Guinda"},
    "1325": {"lat": -18.121686, "lon": -43.549112, "source": "nominatim:Mendanha"},
    "1317": {"lat": -18.005000, "lon": -43.553401, "source": "nominatim:Maria Nunes"},
    "1350": {"lat": -18.080170, "lon": -43.634096, "source": "nominatim:Pinheiro"},
    "1414": {"lat": -18.310020, "lon": -43.523591, "source": "nominatim:Extracao"},
    "1287": {"lat": -18.416567, "lon": -43.525072, "source": "nominatim:Vau"},
}

# ---- Manual estimates for 12 remaining places ----
# Based on neighborhood/district knowledge of Diamantina
MANUAL = {
    # Urban schools - neighborhood-level coordinates
    # E. E. PROF.ª GABRIELA NEVES - Bairro Palha (north-east of center)
    "1180": {"lat": -18.234, "lon": -43.596, "source": "manual:bairro_palha"},
    # E. E. PROF.ª ISABEL MOTA - Bairro Bom Jesus (south-west of center)
    "1236": {"lat": -18.249, "lon": -43.608, "source": "manual:bairro_bom_jesus"},
    # E. E. PROF. JOSÉ AUGUSTO NEVES - Bairro Rio Grande (south-east)
    "1155": {"lat": -18.252, "lon": -43.594, "source": "manual:bairro_rio_grande"},
    # E. E. PROF.ª AYNA TORRES - Travessa da Glória (center)
    "1244": {"lat": -18.244, "lon": -43.601, "source": "manual:trav_gloria"},
    # E. M. DE ED. INFANTIL PROF. CÉLIO HUGO (ANTIGO SESI) - Bairro Rio Grande
    "1465": {"lat": -18.254, "lon": -43.592, "source": "manual:bairro_rio_grande"},
    # E. E. DONA GUIDINHA - Praça da Matriz (Cathedral square, downtown)
    "1260": {"lat": -18.248, "lon": -43.601, "source": "manual:praca_matriz"},

    # Rural schools - district/povoado estimates
    # E. E. DURVAL CÂNDIDO CRUZ - R PRINCIPAL in a district (likely Planalto de Minas or similar)
    "1333": {"lat": -18.300, "lon": -43.490, "source": "manual:distrito_planalto_minas"},
    # E. M. BATATAL - Povoado de Batatal
    "1457": {"lat": -18.190, "lon": -43.560, "source": "manual:povoado_batatal"},
    # E. M. BAIXADÃO - Povoado de Baixadão
    "1406": {"lat": -18.350, "lon": -43.500, "source": "manual:povoado_baixadao"},
    # E. M. PEDRARIA - Distrito Senador Mourão
    "1384": {"lat": -18.200, "lon": -43.750, "source": "manual:senador_mourao"},
    # E. M. MÃO TORTA - Povoado Mão Torta
    "1422": {"lat": -18.150, "lon": -43.660, "source": "manual:povoado_mao_torta"},
    # E. M. PEDRO BAIANO - Povoado Pedro Baiano
    "1392": {"lat": -18.320, "lon": -43.550, "source": "manual:povoado_pedro_baiano"},
}

def main():
    from app.db import session_scope
    from sqlalchemy import text

    # Load polling places from DB
    with session_scope() as session:
        rows = session.execute(
            text("""
                SELECT
                    metadata->>'polling_place_code' AS code,
                    metadata->>'polling_place_name' AS name,
                    COUNT(*) AS sections,
                    SUM(COALESCE((metadata->>'voters_section')::int, 0)) AS total_voters
                FROM silver.dim_territory
                WHERE level = 'electoral_section'
                  AND municipality_ibge_code = '3121605'
                  AND metadata->>'polling_place_code' IS NOT NULL
                GROUP BY 1, 2
                ORDER BY total_voters DESC
            """),
        ).fetchall()

    # Build comprehensive seed
    all_coords = {**GEOCODED, **MANUAL}

    os.makedirs("data/seed", exist_ok=True)
    path = "data/seed/polling_places_diamantina.csv"

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["polling_place_code", "polling_place_name", "latitude", "longitude",
                     "source", "sections", "voters"])
        matched = 0
        for r in rows:
            code, name, sections, voters = r[0], r[1], int(r[2]), int(r[3])
            if code in all_coords:
                c = all_coords[code]
                w.writerow([code, name, c["lat"], c["lon"], c["source"], sections, voters])
                matched += 1
            else:
                w.writerow([code, name, "", "", "unmatched", sections, voters])
                print(f"  WARNING: No coords for {name} ({code})")

    print(f"\nSaved {path}")
    print(f"  {matched}/{len(rows)} places have coordinates")
    print(f"  Nominatim: {len(GEOCODED)}" )
    print(f"  Manual:    {len(MANUAL)}")
    print(f"  Total:     {matched}")

if __name__ == "__main__":
    main()
