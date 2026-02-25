"""
Targeted geocoding for remaining/suspicious polling places.
Uses INEP address + district/village-specific Nominatim queries.
"""
from __future__ import annotations
import json, sys, time, math
import httpx
sys.path.insert(0, "src")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
DELAY = 1.1
UA = "territorial-intelligence-platform/1.0"
CENTER = (-18.2337, -43.6021)

def _dist_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def nominatim(query, max_dist=50):
    """Try Nominatim query, return (lat, lon, display) or None."""
    client = httpx.Client(timeout=15, headers={"User-Agent": UA})
    try:
        r = client.get(NOMINATIM_URL, params={"q": query, "format": "json", "limit": 3, "countrycodes": "br"})
        time.sleep(DELAY)
        if r.status_code == 200:
            for hit in r.json():
                lat, lon = float(hit["lat"]), float(hit["lon"])
                d = _dist_km(lat, lon, CENTER[0], CENTER[1])
                if d <= max_dist:
                    return lat, lon, hit.get("display_name",""), d
    except:
        pass
    finally:
        client.close()
    return None

# ---- Places to resolve ----
# Format: (code, name, [list of queries to try], max_dist)
targets = [
    # URBAN - Wrong results (> 30km) that need re-geocoding
    ("1180", "E. E. PROF.ª GABRIELA NEVES", [
        "Rua da Palha, 1666, Palha, Diamantina, MG",
        "Escola Estadual Professora Gabriela Neves, Diamantina, MG",
        "Bairro Palha, Diamantina, MG",
    ], 10),
    ("1309", "E. E. JOÃO CÉSAR DE OLIVEIRA", [
        "Rua da Várzea, Inhaí, Diamantina, MG",
        "Escola Estadual João César de Oliveira, Diamantina, MG",
        "Inhaí, Diamantina, MG",
        "Distrito de Inhaí, Diamantina, Minas Gerais",
    ], 50),
    ("1333", "E. E. DURVAL CÂNDIDO CRUZ", [
        "Escola Estadual Durval Cândido Cruz, Diamantina, MG",
        "São Gonçalo do Rio das Pedras, Diamantina, MG",
        "Distrito São Gonçalo do Rio das Pedras, Diamantina",
    ], 50),
    ("1252", "E. E. D. JOAQUIM SILVÉRIO DE SOUZA", [
        "Escola Estadual Dom Joaquim Silvério de Souza, Diamantina, MG",
        "Conselheiro Mata, Diamantina, MG",
        "Distrito de Conselheiro Mata, Diamantina, Minas Gerais",
    ], 50),

    # URBAN - Unmatched with INEP addresses
    ("1236", "E. E. PROF.ª ISABEL MOTA", [
        "Rua Elvira Ramos Couto, 319, Bom Jesus, Diamantina, MG",
        "Rua Elvira Ramos Couto, Diamantina, MG",
        "Bairro Bom Jesus, Diamantina, MG",
        "Escola Estadual Professora Isabel Motta, Diamantina, MG",
    ], 10),
    ("1015", "UEMG (ANTIGA FEVALE)", [
        "UEMG Diamantina, MG",
        "Universidade do Estado de Minas Gerais, Diamantina, MG",
        "FAFIDIA, Diamantina, MG",
        "Rua da Glória, 394, Diamantina, MG",
    ], 10),
    ("1155", "E. E. PROF. JOSÉ AUGUSTO NEVES", [
        "Travessa Coronel Caetano Mascarenhas, 150, Rio Grande, Diamantina, MG",
        "Travessa Coronel Caetano Mascarenhas, Diamantina, MG",
        "Bairro Rio Grande, Diamantina, MG",
        "Escola Estadual Professor José Augusto Neves, Diamantina, MG",
    ], 10),
    ("1244", "E. E. PROF.ª AYNA TORRES", [
        "Rua Professor Paulino Guimarães Júnior, Diamantina, MG",
        "Travessa da Glória, Diamantina, MG",
        "Escola Estadual Professora Ayna Torres, Diamantina, MG",
    ], 10),
    ("1465", "E. M. DE ED. INFANTIL PROF. CÉLIO HUGO ALVES PEREIRA (ANTIGO SESI)", [
        "Rua do Areão, 333, Rio Grande, Diamantina, MG",
        "Rua do Areão, Diamantina, MG",
        "Bairro Rio Grande, Diamantina, MG",
    ], 10),
    ("1260", "E. E. DONA GUIDINHA", [
        "Praça da Matriz, Diamantina, MG",
        "Escola Estadual Dona Guidinha, Diamantina, MG",
        "Praça da Sé, Diamantina, MG",
    ], 10),
    ("1228", "E. M. CASA DA CRIANÇA MARIA ANTONIA", [
        "Rua Cruz de Moisés, 364, Consolação, Diamantina, MG",
        "Rua Cruz de Moisés, Diamantina, MG",
        "Bairro Consolação, Diamantina, MG",
    ], 10),

    # RURAL - District/village schools
    ("1341", "E. E. GOV. JUSCELINO KUBITSCHEK", [
        "Escola Estadual Governador Juscelino Kubitschek, Diamantina, MG",
        "Conselheiro Mata, Diamantina, MG",
        "Distrito de Conselheiro Mata, Diamantina",
    ], 50),
    ("1376", "E. M. SOPA", [
        "Distrito de Sopa, Diamantina, MG",
        "Sopa, Diamantina, Minas Gerais",
        "Praça Santa Rita, Sopa, Diamantina",
    ], 50),
    ("1295", "E. M. GUINDA", [
        "Guinda, Diamantina, MG",
        "Povoado de Guinda, Diamantina, Minas Gerais",
    ], 50),
    ("1325", "E. M. PROF.ª ANA CÉLIA DE O. SOUZA", [
        "Largo do Areão, Mendanha, Diamantina, MG",
        "Mendanha, Diamantina, MG",
        "Povoado de Mendanha, Diamantina, Minas Gerais",
    ], 50),
    ("1317", "E. M. MARIA NUNES", [
        "Povoado de Maria Nunes, Diamantina, MG",
        "Maria Nunes, Diamantina, Minas Gerais",
    ], 50),
    ("1350", "E. M. PINHEIRO", [
        "Povoado de Pinheiro, Diamantina, MG",
        "Pinheiro, Diamantina, Minas Gerais",
    ], 50),
    ("1414", "E. M. ROGÉRIO FIRMINO LOPES", [
        "Rua Edmar Santos, Extração, Diamantina, MG",
        "Extração, Diamantina, MG",
        "Distrito de Extração, Diamantina",
    ], 50),
    ("1457", "E. M. BATATAL", [
        "Povoado de Batatal, Diamantina, MG",
        "Batatal, Diamantina, Minas Gerais",
    ], 50),
    ("1287", "RECEPTIVO VILA REAL DO VAU", [
        "Vila Real do Vau, Diamantina, MG",
        "Vau, Diamantina, MG",
        "Biribiri, Diamantina, MG",
    ], 50),
    ("1406", "E. M. BAIXADÃO", [
        "Povoado de Baixadão, Diamantina, MG",
        "Baixadão, Diamantina, Minas Gerais",
    ], 50),
    ("1384", "E. M. PEDRARIA", [
        "Povoado de Pedraria, Diamantina, MG",
        "Pedraria, Diamantina, Minas Gerais",
        "Senador Mourão, Diamantina, MG",
    ], 50),
    ("1422", "E. M. MÃO TORTA", [
        "Povoado Mão Torta, Diamantina, MG",
        "Mão Torta, Diamantina, Minas Gerais",
    ], 50),
    ("1392", "E. M. PEDRO BAIANO", [
        "Povoado de Pedro Baiano, Diamantina, MG",
        "Pedro Baiano, Diamantina, Minas Gerais",
    ], 50),
]

def main():
    results = {}
    for code, name, queries, max_dist in targets:
        print(f"\n--- {name} ({code}) ---")
        found = False
        for q in queries:
            r = nominatim(q, max_dist)
            if r:
                lat, lon, display, dist = r
                print(f"  OK: ({lat:.6f}, {lon:.6f}) dist={dist:.1f}km")
                print(f"      query: {q}")
                print(f"      display: {display[:80]}")
                results[code] = {"name": name, "lat": lat, "lon": lon, "source": f"nominatim:{q}", "dist": dist}
                found = True
                break
            else:
                print(f"  miss: {q}")
        if not found:
            print(f"  FAILED: no result within {max_dist}km")
            results[code] = {"name": name, "lat": None, "lon": None, "source": "unmatched"}

    # Summary
    ok = sum(1 for v in results.values() if v["lat"])
    fail = sum(1 for v in results.values() if not v["lat"])
    print(f"\n{'='*60}")
    print(f"RESULTS: {ok} OK, {fail} FAILED out of {len(targets)}")
    print(f"{'='*60}")
    for code, v in results.items():
        if v["lat"]:
            print(f"  OK   {code}: {v['name']} -> ({v['lat']:.6f}, {v['lon']:.6f}) [{v['dist']:.1f}km]")
        else:
            print(f"  FAIL {code}: {v['name']}")

    with open("geocode_targeted_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to geocode_targeted_results.json")

if __name__ == "__main__":
    main()
