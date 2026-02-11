from __future__ import annotations

import argparse
import ftplib
import io
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MANUAL_DIR = DATA_DIR / "manual"
RAW_DIR = DATA_DIR / "raw" / "bootstrap"

MTE_FTP_HOST = "ftp.mtps.gov.br"
MTE_FTP_ROOT = "/pdet/microdados/NOVO CAGED"

SENATRAN_PAGE_TEMPLATE = (
    "https://www.gov.br/transportes/pt-br/assuntos/transito/"
    "conteudo-Senatran/frota-de-veiculos-{year}"
)
SENATRAN_FALLBACK_CSV = (
    "https://www.gov.br/transportes/pt-br/assuntos/transito/"
    "conteudo-Senatran/FrotaporMunicipioetipoJulho2025.csv"
)
SEJUSP_PAGE = "https://www.seguranca.mg.gov.br/index.php/transparencia/dados-abertos"
SIOPS_BASE = "https://siops-consulta-publica-api.saude.gov.br"
SNIS_PAGE = (
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
    "saneamento/snis/area-do-prestador-e-municipios"
)


@dataclass
class SourceResult:
    source: str
    status: str
    output_file: str | None = None
    details: dict[str, Any] | None = None
    error: str | None = None


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().casefold())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _to_int(value: Any) -> int:
    token = str(value or "").strip()
    token = token.replace(".", "").replace(",", "")
    token = re.sub(r"[^0-9-]", "", token)
    if not token or token == "-":
        return 0
    try:
        return int(token)
    except ValueError:
        return 0


def _to_float_br(value: Any) -> float:
    token = str(value or "").strip()
    token = token.replace("%", "").replace("R$", "").replace(" ", "")
    if "," in token and "." in token:
        token = token.replace(".", "").replace(",", ".")
    else:
        token = token.replace(",", ".")
    token = re.sub(r"[^0-9.-]", "", token)
    if not token or token == "-":
        return 0.0
    try:
        return float(token)
    except ValueError:
        return 0.0


def _session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


def _ensure_dirs() -> None:
    for path in (
        MANUAL_DIR / "mte",
        MANUAL_DIR / "senatran",
        MANUAL_DIR / "sejusp",
        MANUAL_DIR / "siops",
        MANUAL_DIR / "snis",
        RAW_DIR / "mte",
        RAW_DIR / "senatran",
        RAW_DIR / "sejusp",
        RAW_DIR / "siops",
        RAW_DIR / "snis",
    ):
        path.mkdir(parents=True, exist_ok=True)


def _extract_7z(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)

    try:
        import py7zr  # type: ignore

        with py7zr.SevenZipFile(archive_path, mode="r") as archive:
            archive.extractall(path=destination)
        return
    except Exception:
        pass

    seven_zip_bin = shutil.which("7z")
    if seven_zip_bin:
        result = subprocess.run(
            [seven_zip_bin, "x", str(archive_path), f"-o{destination}", "-y"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return
        raise RuntimeError(f"7z extraction failed: {result.stderr.strip()}")

    tar_bin = shutil.which("tar")
    if tar_bin:
        result = subprocess.run(
            [tar_bin, "-xf", str(archive_path), "-C", str(destination)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return
        raise RuntimeError(f"tar extraction failed: {result.stderr.strip()}")

    raise RuntimeError(
        "No .7z extractor available. Install py7zr, 7-Zip, or tar/libarchive support."
    )


def _pick_first_file(paths: list[Path], suffixes: set[str]) -> Path | None:
    candidates = [p for p in paths if p.is_file() and p.suffix.casefold() in suffixes]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_size, reverse=True)[0]


def bootstrap_mte(reference_year: str) -> SourceResult:
    source = "MTE"
    try:
        raw_dir = RAW_DIR / "mte"
        manual_dir = MANUAL_DIR / "mte"
        ftp = ftplib.FTP()
        ftp.connect(MTE_FTP_HOST, 21, timeout=30)
        ftp.login()
        ftp.encoding = "latin-1"
        ftp.cwd(f"{MTE_FTP_ROOT}/{reference_year}")
        month_dirs = [name for name in ftp.nlst() if name.isdigit() and len(name) == 6]
        if not month_dirs:
            ftp.quit()
            raise RuntimeError(f"No month directories found in FTP for year {reference_year}.")
        month_dir = sorted(month_dirs)[-1]
        ftp.cwd(f"{MTE_FTP_ROOT}/{reference_year}/{month_dir}")
        file_names = ftp.nlst()
        preferred = [n for n in file_names if n.upper().startswith("CAGEDMOV") and n.endswith(".7z")]
        if not preferred:
            preferred = [n for n in file_names if n.endswith(".7z")]
        if not preferred:
            ftp.quit()
            raise RuntimeError("No .7z file found in selected MTE FTP month directory.")
        selected_file = sorted(preferred)[-1]

        raw_archive_path = raw_dir / selected_file
        with raw_archive_path.open("wb") as fp:
            ftp.retrbinary(f"RETR {selected_file}", fp.write)
        ftp.quit()

        extracted_dir = raw_dir / f"extract_{reference_year}_{month_dir}"
        if extracted_dir.exists():
            shutil.rmtree(extracted_dir, ignore_errors=True)
        extracted_dir.mkdir(parents=True, exist_ok=True)
        _extract_7z(raw_archive_path, extracted_dir)
        all_files = list(extracted_dir.rglob("*"))
        tabular = _pick_first_file(all_files, {".csv", ".txt", ".zip"})
        if tabular is None:
            raise RuntimeError("No CSV/TXT/ZIP file found after extracting MTE .7z.")
        output_path = manual_dir / f"mte_novo_caged_{reference_year}{tabular.suffix.casefold()}"
        shutil.copy2(tabular, output_path)

        return SourceResult(
            source=source,
            status="ok",
            output_file=str(output_path.relative_to(PROJECT_ROOT)),
            details={
                "ftp_host": MTE_FTP_HOST,
                "ftp_year": reference_year,
                "ftp_month_dir": month_dir,
                "ftp_file": selected_file,
            },
        )
    except Exception as exc:
        return SourceResult(source=source, status="error", error=str(exc))


def _parse_senatran_csv(text: str, municipality_name: str) -> dict[str, Any]:
    lines = text.splitlines()
    header_idx = next(
        (idx for idx, line in enumerate(lines) if line.startswith("UF,MUNICIPIO,TOTAL")),
        None,
    )
    if header_idx is None:
        raise RuntimeError("Could not find expected header row in SENATRAN CSV.")
    clean_csv = "\n".join(lines[header_idx:])
    df = pd.read_csv(io.StringIO(clean_csv), sep=",", dtype=str)
    df = df[df["UF"] != "UF"].copy()
    target = _normalize_text(municipality_name)
    df["_municipio_norm"] = df["MUNICIPIO"].astype(str).map(_normalize_text)
    selected = df[df["_municipio_norm"] == target]
    if selected.empty:
        raise RuntimeError(f"Municipality '{municipality_name}' not found in SENATRAN dataset.")
    row = selected.iloc[0]
    return {
        "municipio": municipality_name,
        "frota_total": _to_int(row.get("TOTAL")),
        "motocicleta": _to_int(row.get("MOTOCICLETA")) + _to_int(row.get("MOTONETA")),
        "automovel": _to_int(row.get("AUTOMOVEL")),
        "onibus": _to_int(row.get("ONIBUS")) + _to_int(row.get("MICRO-ONIBUS")),
    }


def bootstrap_senatran(reference_year: str, municipality_name: str) -> SourceResult:
    source = "SENATRAN"
    try:
        session = _session()
        page_url = SENATRAN_PAGE_TEMPLATE.format(year=reference_year)
        page_resp = session.get(page_url, timeout=30)
        page_resp.raise_for_status()
        links = re.findall(r'href="([^"]+)"', page_resp.text, flags=re.IGNORECASE)
        csv_candidates: list[str] = []
        for link in links:
            full = urljoin(page_url, link)
            normalized = _normalize_text(unquote(full))
            if "frotapormunicipioetipo" in normalized and normalized.endswith(".csv"):
                csv_candidates.append(full)
        selected_csv = sorted(set(csv_candidates))[-1] if csv_candidates else SENATRAN_FALLBACK_CSV

        raw_path = RAW_DIR / "senatran" / Path(selected_csv).name
        raw_resp = session.get(selected_csv, timeout=60)
        raw_resp.raise_for_status()
        raw_path.write_bytes(raw_resp.content)

        parsed = _parse_senatran_csv(raw_resp.text, municipality_name)
        output_path = MANUAL_DIR / "senatran" / f"senatran_diamantina_{reference_year}.csv"
        pd.DataFrame([parsed]).to_csv(output_path, index=False, sep=";")

        return SourceResult(
            source=source,
            status="ok",
            output_file=str(output_path.relative_to(PROJECT_ROOT)),
            details={
                "source_page": page_url,
                "download_url": selected_csv,
                "raw_file": str(raw_path.relative_to(PROJECT_ROOT)),
            },
        )
    except Exception as exc:
        return SourceResult(source=source, status="error", error=str(exc))


def _pick_sejusp_link(links: list[str], required_keywords: list[str]) -> str:
    for link in links:
        norm = _normalize_text(unquote(link))
        if all(keyword in norm for keyword in required_keywords):
            return link
    raise RuntimeError(f"Could not find SEJUSP CSV link for keywords: {required_keywords}")


def _load_sejusp_csv(session: requests.Session, url: str) -> pd.DataFrame:
    response = session.get(url, timeout=90)
    response.raise_for_status()
    raw_path = RAW_DIR / "sejusp" / Path(url).name
    raw_path.write_bytes(response.content)
    return pd.read_csv(io.BytesIO(response.content), sep=";", encoding="utf-8", low_memory=False)


def _sum_sejusp_registros(
    df: pd.DataFrame,
    municipality_ibge_code: str,
    reference_year: str,
) -> float:
    target_code = municipality_ibge_code[:6]
    filtered = df.copy()
    if "Cód. IBGE" in filtered.columns:
        filtered["Cód. IBGE"] = filtered["Cód. IBGE"].astype(str).str.replace(r"\.0$", "", regex=True)
        filtered = filtered[filtered["Cód. IBGE"].str.startswith(target_code)]
    if "Ano Fato" in filtered.columns:
        filtered = filtered[filtered["Ano Fato"].astype(str) == reference_year]
    if "Registros" not in filtered.columns:
        return 0.0
    return float(pd.to_numeric(filtered["Registros"], errors="coerce").fillna(0).sum())


def bootstrap_sejusp(
    municipality_name: str,
    municipality_ibge_code: str,
    reference_year: str,
) -> SourceResult:
    source = "SEJUSP_MG"
    try:
        session = _session()
        page_resp = session.get(SEJUSP_PAGE, timeout=30)
        page_resp.raise_for_status()
        links = re.findall(r'href="([^"]+)"', page_resp.text, flags=re.IGNORECASE)
        csv_links: list[str] = []
        for link in links:
            full = urljoin(SEJUSP_PAGE, link)
            norm = _normalize_text(unquote(full))
            if "/images/" in full.lower() and norm.endswith(".csv"):
                csv_links.append(full)
        csv_links = sorted(set(csv_links))
        if not csv_links:
            raise RuntimeError("No CSV links found on SEJUSP open data page.")

        violent_link = _pick_sejusp_link(csv_links, ["crimes", "violentos", "2025", "diante"])
        robbery_link = _pick_sejusp_link(csv_links, ["alvos", "roubo"])
        theft_link = _pick_sejusp_link(csv_links, ["alvos", "furto"])

        violent_df = _load_sejusp_csv(session, violent_link)
        robbery_df = _load_sejusp_csv(session, robbery_link)
        theft_df = _load_sejusp_csv(session, theft_link)

        crimes_violentos = _sum_sejusp_registros(violent_df, municipality_ibge_code, reference_year)
        roubos = _sum_sejusp_registros(robbery_df, municipality_ibge_code, reference_year)
        furtos = _sum_sejusp_registros(theft_df, municipality_ibge_code, reference_year)

        output_path = MANUAL_DIR / "sejusp" / f"sejusp_diamantina_{reference_year}.csv"
        pd.DataFrame(
            [
                {
                    "codigo_municipio": municipality_ibge_code,
                    "municipio": municipality_name,
                    "ocorrencias_total": crimes_violentos,
                    "crimes_violentos": crimes_violentos,
                    "roubos": roubos,
                    "furtos": furtos,
                }
            ]
        ).to_csv(output_path, index=False, sep=";")

        return SourceResult(
            source=source,
            status="ok",
            output_file=str(output_path.relative_to(PROJECT_ROOT)),
            details={
                "source_page": SEJUSP_PAGE,
                "violent_link": violent_link,
                "robbery_link": robbery_link,
                "theft_link": theft_link,
            },
        )
    except Exception as exc:
        return SourceResult(source=source, status="error", error=str(exc))


def _siops_get_json(session: requests.Session, url: str) -> tuple[int, Any]:
    response = session.get(url, timeout=40)
    if response.status_code != 200:
        return response.status_code, None
    try:
        return 200, response.json()
    except Exception:
        return response.status_code, None


def bootstrap_siops(municipality_ibge_code: str, reference_year: str) -> SourceResult:
    source = "SIOPS"
    try:
        municipality6 = municipality_ibge_code[:6]
        uf_code = municipality_ibge_code[:2]
        session = _session()

        status, periods_payload = _siops_get_json(session, f"{SIOPS_BASE}/v1/ano-periodo")
        if status != 200 or not isinstance(periods_payload, list):
            raise RuntimeError("Could not load SIOPS period catalog.")

        periods_by_year: dict[str, list[int]] = {}
        for item in periods_payload:
            year = str(item.get("ds_ano", "")).strip()
            period_token = str(item.get("nu_periodo", "")).strip()
            if not year or not period_token.isdigit():
                continue
            periods_by_year.setdefault(year, []).append(int(period_token))
        for year in periods_by_year:
            periods_by_year[year] = sorted(set(periods_by_year[year]), reverse=True)

        year_candidates = [reference_year]
        for shift in range(1, 6):
            year_candidates.append(str(int(reference_year) - shift))

        selected_year: str | None = None
        selected_period: int | None = None
        indicator_payload: list[dict[str, Any]] | None = None

        for year in year_candidates:
            for period in periods_by_year.get(year, []):
                indicator_url = (
                    f"{SIOPS_BASE}/v1/indicador/municipal/{municipality6}/{year}/{period}"
                )
                status, payload = _siops_get_json(session, indicator_url)
                if status == 200 and isinstance(payload, list) and payload:
                    selected_year = year
                    selected_period = period
                    indicator_payload = payload
                    break
            if selected_year is not None:
                break

        if selected_year is None or selected_period is None or indicator_payload is None:
            raise RuntimeError(
                "Could not get SIOPS indicator payload for requested municipality/year window."
            )

        rreo_url = (
            f"{SIOPS_BASE}/v1/rreo/municipal/{uf_code}/{municipality6}/"
            f"{selected_year}/{selected_period}"
        )
        status, rreo_payload = _siops_get_json(session, rreo_url)
        if status != 200 or not isinstance(rreo_payload, list):
            raise RuntimeError("Could not get SIOPS RREO payload.")

        per_capita = 0.0
        percentual_receita = 0.0
        for row in indicator_payload:
            description = _normalize_text(str(row.get("ds_indicador", "")))
            value = _to_float_br(row.get("indicador_calculado"))
            if "por habitante" in description:
                per_capita = value
            if "receita propria aplicada em asps" in description:
                percentual_receita = value

        despesa_total = 0.0
        for row in rreo_payload:
            if str(row.get("coItem", "")).strip() == "6043":
                despesa_total = _to_float_br(
                    row.get("vl_coluna3") or row.get("vl_coluna2") or row.get("vl_coluna1")
                )
                break
        if despesa_total == 0.0:
            for row in rreo_payload:
                if "total das despesas com asps" in _normalize_text(str(row.get("dsItem", ""))):
                    despesa_total = _to_float_br(
                        row.get("vl_coluna3") or row.get("vl_coluna2") or row.get("vl_coluna1")
                    )
                    break

        output_path = MANUAL_DIR / "siops" / f"siops_diamantina_{selected_year}.csv"
        pd.DataFrame(
            [
                {
                    "codigo_municipio": f"{municipality6}5",
                    "municipio": "Diamantina",
                    "despesa_total_saude": despesa_total,
                    "despesa_saude_per_capita": per_capita,
                    "percentual_receita_propria_saude": percentual_receita,
                }
            ]
        ).to_csv(output_path, index=False, sep=";")

        return SourceResult(
            source=source,
            status="ok",
            output_file=str(output_path.relative_to(PROJECT_ROOT)),
            details={
                "selected_year": selected_year,
                "selected_period": selected_period,
            },
        )
    except Exception as exc:
        return SourceResult(source=source, status="error", error=str(exc))


def bootstrap_snis_probe() -> SourceResult:
    source = "SNIS"
    try:
        session = _session()
        response = session.get(SNIS_PAGE, timeout=30)
        response.raise_for_status()
        links = re.findall(r'href="([^"]+)"', response.text, flags=re.IGNORECASE)
        file_links = [
            urljoin(SNIS_PAGE, link)
            for link in links
            if any(ext in link.lower() for ext in (".csv", ".xlsx", ".xls", ".zip"))
        ]
        if not file_links:
            return SourceResult(
                source=source,
                status="manual_required",
                details={
                    "reason": "No stable file link discovered automatically on SNIS page.",
                    "page": SNIS_PAGE,
                },
            )
        return SourceResult(
            source=source,
            status="manual_required",
            details={
                "reason": "Auto discovery found files, but no deterministic schema link selected.",
                "sample_links": file_links[:5],
            },
        )
    except Exception as exc:
        return SourceResult(source=source, status="manual_required", error=str(exc))


def _dump_report(results: list[SourceResult], report_path: Path) -> None:
    payload = {
        "results": [
            {
                "source": result.source,
                "status": result.status,
                "output_file": result.output_file,
                "details": result.details or {},
                "error": result.error,
            }
            for result in results
        ]
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bootstrap manual source files for local fallback connectors."
    )
    parser.add_argument("--reference-year", default="2025")
    parser.add_argument("--municipality-name", default="Diamantina")
    parser.add_argument("--municipality-ibge-code", default="3121605")
    parser.add_argument(
        "--report-path",
        default=str(DATA_DIR / "manual" / "bootstrap_report.json"),
    )
    parser.add_argument("--skip-mte", action="store_true")
    parser.add_argument("--skip-senatran", action="store_true")
    parser.add_argument("--skip-sejusp", action="store_true")
    parser.add_argument("--skip-siops", action="store_true")
    parser.add_argument("--skip-snis-probe", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _ensure_dirs()

    results: list[SourceResult] = []

    if not args.skip_mte:
        results.append(bootstrap_mte(args.reference_year))
    if not args.skip_senatran:
        results.append(bootstrap_senatran(args.reference_year, args.municipality_name))
    if not args.skip_sejusp:
        results.append(
            bootstrap_sejusp(
                municipality_name=args.municipality_name,
                municipality_ibge_code=args.municipality_ibge_code,
                reference_year=args.reference_year,
            )
        )
    if not args.skip_siops:
        results.append(
            bootstrap_siops(
                municipality_ibge_code=args.municipality_ibge_code,
                reference_year=args.reference_year,
            )
        )
    if not args.skip_snis_probe:
        results.append(bootstrap_snis_probe())

    report_path = Path(args.report_path)
    _dump_report(results, report_path)

    print(json.dumps({"report_path": str(report_path), "results": [r.__dict__ for r in results]}, ensure_ascii=False, indent=2))
    has_error = any(result.status == "error" for result in results)
    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
