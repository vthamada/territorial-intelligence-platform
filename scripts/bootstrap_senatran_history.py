from __future__ import annotations

import argparse
import io
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

DEFAULT_URLS_BY_YEAR: dict[str, str] = {
    "2021": (
        "https://www.gov.br/transportes/pt-br/assuntos/transito/arquivos-senatran/"
        "estatisticas/renavam/2021/dezembro/frota-munic-modelo-dezembro-2021.xls"
    ),
    "2022": (
        "https://www.gov.br/transportes/pt-br/assuntos/transito/arquivos-senatran/"
        "estatisticas/renavam/2022/dezembro/frota_munic_modelo_dezembro_2022.xls"
    ),
    "2023": (
        "https://www.gov.br/transportes/pt-br/assuntos/transito/arquivos-senatran/"
        "estatisticas/renavam/2023/Dezembro/frota_munic_modelo_dezembro_2023.xls"
    ),
    "2024": (
        "https://www.gov.br/transportes/pt-br/assuntos/transito/"
        "conteudo-Senatran/FrotapormunicipioetipoDezembro2024.xlsx"
    ),
    "2025": (
        "https://www.gov.br/transportes/pt-br/assuntos/transito/"
        "conteudo-Senatran/FrotaporMunicipioetipoJulho2025.csv"
    ),
}

OUTPUT_DIR = Path("data/manual/senatran")


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value).strip().casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _normalize_column_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _normalize_text(value)).strip("_")


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    token = str(value).strip()
    if not token or token in {"nan", "None", "-"}:
        return 0
    token = token.replace(".", "").replace(" ", "")
    if token.count(",") > 1:
        token = token.replace(",", "")
    else:
        token = token.replace(",", ".")
    token = re.sub(r"[^0-9.-]", "", token)
    if not token or token == "-":
        return 0
    try:
        return int(float(token))
    except ValueError:
        return 0


def _load_tabular(raw_bytes: bytes, source_url: str) -> pd.DataFrame:
    suffix = Path(source_url).suffix.casefold()
    if suffix in {".xls", ".xlsx"}:
        return pd.read_excel(io.BytesIO(raw_bytes), dtype=str)
    if suffix == ".csv":
        return pd.read_csv(io.BytesIO(raw_bytes), sep=",", dtype=str, low_memory=False)
    raise ValueError(f"Unsupported SENATRAN source extension: {suffix}")


def _reshape_with_embedded_header(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("Empty SENATRAN dataset.")

    first_column = df.columns[0]
    header_idx = None
    for index in range(len(df)):
        cell = df.iloc[index, 0]
        if _normalize_text(str(cell)) == "uf":
            header_idx = index
            break
    if header_idx is None:
        # For CSV sources that already arrive with proper columns.
        if _normalize_text(str(first_column)) == "uf":
            return df.copy()
        raise ValueError("Could not locate SENATRAN header row ('UF').")

    header = [str(value).strip() for value in df.iloc[header_idx].tolist()]
    trimmed = df.iloc[header_idx + 1 :].copy()
    trimmed.columns = header
    return trimmed


def _extract_diamantina_row(df: pd.DataFrame, municipality_name: str) -> pd.Series:
    cleaned = df.copy()
    cleaned = cleaned.rename(columns={col: _normalize_column_name(col) for col in cleaned.columns})

    if "municipio" not in cleaned.columns:
        raise ValueError("Missing MUNICIPIO column in SENATRAN dataset.")

    if "uf" in cleaned.columns:
        cleaned = cleaned[cleaned["uf"].astype(str).str.upper() == "MG"]
    cleaned = cleaned[cleaned["municipio"].astype(str).str.strip() != ""]
    cleaned = cleaned[cleaned["municipio"].astype(str).str.upper() != "MUNICIPIO"]
    target = _normalize_text(municipality_name)
    filtered = cleaned[cleaned["municipio"].astype(str).map(_normalize_text) == target]
    if filtered.empty:
        raise ValueError(f"Municipality '{municipality_name}' not found in SENATRAN dataset.")
    return filtered.iloc[0]


def _build_output_row(row: pd.Series, municipality_ibge_code: str, municipality_name: str) -> dict[str, Any]:
    total = _to_int(row.get("total"))
    motorcycles = _to_int(row.get("motocicleta")) + _to_int(row.get("motoneta"))
    cars = _to_int(row.get("automovel"))
    buses = _to_int(row.get("onibus")) + _to_int(row.get("micro_onibus"))
    return {
        "codigo_municipio": municipality_ibge_code,
        "municipio": municipality_name,
        "frota_total": total,
        "motocicleta": motorcycles,
        "automovel": cars,
        "onibus": buses,
    }


def bootstrap_senatran_years(
    *,
    years: list[str],
    municipality_name: str,
    municipality_ibge_code: str,
) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"results": []}
    client = httpx.Client(timeout=90, follow_redirects=True, trust_env=False)
    try:
        for year in years:
            url = DEFAULT_URLS_BY_YEAR.get(year)
            if not url:
                report["results"].append(
                    {
                        "year": year,
                        "status": "blocked",
                        "reason": "no_source_url_mapped",
                    }
                )
                continue

            try:
                response = client.get(url)
                response.raise_for_status()
                df = _load_tabular(response.content, url)
                shaped = _reshape_with_embedded_header(df)
                municipality_row = _extract_diamantina_row(shaped, municipality_name)
                output_row = _build_output_row(
                    municipality_row,
                    municipality_ibge_code=municipality_ibge_code,
                    municipality_name=municipality_name,
                )
                output_path = OUTPUT_DIR / f"senatran_diamantina_{year}.csv"
                pd.DataFrame([output_row]).to_csv(output_path, sep=";", index=False)
                report["results"].append(
                    {
                        "year": year,
                        "status": "success",
                        "source_url": url,
                        "output_file": output_path.as_posix(),
                        "frota_total": output_row["frota_total"],
                    }
                )
            except Exception as exc:  # pragma: no cover - runtime safety
                report["results"].append(
                    {
                        "year": year,
                        "status": "failed",
                        "source_url": url,
                        "error": str(exc),
                    }
                )
    finally:
        client.close()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap historical manual SENATRAN files for Diamantina.")
    parser.add_argument("--years", default="2021,2022,2023,2024")
    parser.add_argument("--municipality-name", default="Diamantina")
    parser.add_argument("--municipality-ibge-code", default="3121605")
    parser.add_argument(
        "--report-path",
        default="data/reports/bootstrap_senatran_history_report.json",
    )
    args = parser.parse_args(argv)

    years = [token.strip() for token in args.years.split(",") if token.strip()]
    report = bootstrap_senatran_years(
        years=years,
        municipality_name=args.municipality_name,
        municipality_ibge_code=args.municipality_ibge_code,
    )
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    failed = [item for item in report["results"] if item["status"] != "success"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
