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
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse
from uuid import uuid4

import pandas as pd
import requests
import yaml

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
SNIS_RS_ZIP_URL = (
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
    "saneamento/snis/produtos-do-snis/diagnosticos/"
    "Planilha_RS_2022_atualizado_29112024.zip"
)
SNIS_RS_REFERENCE_YEAR = "2022"
SNIS_RS_INDICATORS_FILE = "Planilha_Indicadores_RS_2022.xlsx"
SNIS_AE_ZIP_URL_TEMPLATE = (
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
    "saneamento/snis/produtos-do-snis/diagnosticos/Planilhas_AE{year}.zip"
)
SNIS_AE_YEARS_LOOKBACK = 6
SNIS_AE_INDICATOR_FIELDS: dict[str, str] = {
    "in055": "atendimento_agua_percentual",
    "in056": "atendimento_esgoto_percentual",
    "in049": "perdas_agua_percentual",
}
SNIS_RS_INDICATOR_FIELDS: dict[str, str] = {
    "in015": "coleta_residuos_percentual",
}

INMET_CATALOG_PATH = PROJECT_ROOT / "configs" / "inmet_climate_catalog.yml"
INPE_QUEIMADAS_CATALOG_PATH = PROJECT_ROOT / "configs" / "inpe_queimadas_catalog.yml"
ANA_CATALOG_PATH = PROJECT_ROOT / "configs" / "ana_hydrology_catalog.yml"
ANATEL_CATALOG_PATH = PROJECT_ROOT / "configs" / "anatel_connectivity_catalog.yml"
ANEEL_CATALOG_PATH = PROJECT_ROOT / "configs" / "aneel_energy_catalog.yml"

_XML_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_XML_NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_XML_NS_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"

_SNIS_CODE_COLUMNS = {
    "codigo_do_ibge",
    "codigo_ibge",
    "codigo_do_municipio",
    "codigo_municipio",
    "cod_ibge",
    "ibge",
}
_SNIS_NAME_COLUMNS = {
    "municipio",
    "nome_municipio",
    "nome_do_municipio",
}


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


def _normalize_column_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _normalize_text(value)).strip("_")


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


def _to_digits(value: Any) -> str:
    token = str(value or "").strip()
    if token.endswith(".0"):
        token = token[:-2]
    return "".join(ch for ch in token if ch.isdigit())


def _xlsx_col_idx(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    if not letters:
        return 0
    index = 0
    for ch in letters:
        index = (index * 26) + (ord(ch.upper()) - 64)
    return max(index - 1, 0)


def _read_xlsx_rows(raw_bytes: bytes, *, preferred_sheet: str | None = None) -> list[list[str]]:
    workbook = zipfile.ZipFile(io.BytesIO(raw_bytes))

    shared_strings: list[str] = []
    if "xl/sharedStrings.xml" in workbook.namelist():
        shared_root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
        for si in shared_root.findall(f"{{{_XML_NS_MAIN}}}si"):
            parts = [node.text or "" for node in si.findall(f".//{{{_XML_NS_MAIN}}}t")]
            shared_strings.append("".join(parts))

    workbook_root = ET.fromstring(workbook.read("xl/workbook.xml"))
    rels_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels_root.findall(f"{{{_XML_NS_PKG}}}Relationship")
    }

    selected_target: str | None = None
    for sheet in workbook_root.findall(f"{{{_XML_NS_MAIN}}}sheets/{{{_XML_NS_MAIN}}}sheet"):
        sheet_name = sheet.attrib.get("name", "")
        rel_id = sheet.attrib.get(f"{{{_XML_NS_REL}}}id", "")
        target = rel_map.get(rel_id, "")
        if not target:
            continue
        if preferred_sheet and preferred_sheet.casefold() not in sheet_name.casefold():
            continue
        selected_target = target
        break

    if selected_target is None:
        first_sheet = workbook_root.find(f"{{{_XML_NS_MAIN}}}sheets/{{{_XML_NS_MAIN}}}sheet")
        if first_sheet is None:
            return []
        rel_id = first_sheet.attrib.get(f"{{{_XML_NS_REL}}}id", "")
        selected_target = rel_map.get(rel_id, "")
        if not selected_target:
            return []

    if not selected_target.startswith("/"):
        selected_target = f"xl/{selected_target}"

    sheet_root = ET.fromstring(workbook.read(selected_target))
    rows: list[list[str]] = []
    for row in sheet_root.findall(f".//{{{_XML_NS_MAIN}}}sheetData/{{{_XML_NS_MAIN}}}row"):
        values_by_col: dict[int, str] = {}
        for cell in row.findall(f"{{{_XML_NS_MAIN}}}c"):
            ref = cell.attrib.get("r", "A1")
            col_index = _xlsx_col_idx(ref)
            cell_type = cell.attrib.get("t")
            value = ""
            if cell_type == "s":
                value_node = cell.find(f"{{{_XML_NS_MAIN}}}v")
                if value_node is not None and value_node.text:
                    try:
                        value = shared_strings[int(value_node.text)]
                    except (ValueError, IndexError):
                        value = value_node.text
            elif cell_type == "inlineStr":
                text_node = cell.find(f"{{{_XML_NS_MAIN}}}is/{{{_XML_NS_MAIN}}}t")
                if text_node is not None and text_node.text:
                    value = text_node.text
            else:
                value_node = cell.find(f"{{{_XML_NS_MAIN}}}v")
                if value_node is not None and value_node.text:
                    value = value_node.text
            values_by_col[col_index] = value

        if not values_by_col:
            rows.append([])
            continue
        width = max(values_by_col.keys()) + 1
        row_values = [""] * width
        for idx, value in values_by_col.items():
            row_values[idx] = value
        rows.append(row_values)
    return rows


def _extract_snis_indicator_metrics(
    rows: list[list[str]],
    *,
    municipality_ibge_code: str,
    municipality_name: str,
    indicator_fields: dict[str, str],
) -> dict[str, Any] | None:
    if not rows:
        return None

    normalized_indicators = {code.casefold(): field for code, field in indicator_fields.items()}
    header_idx: int | None = None
    code_idx: int | None = None
    header_norm: list[str] = []
    code_norm: list[str] = []

    for idx, row in enumerate(rows):
        norm_row = [_normalize_column_name(cell) for cell in row]
        if not any(value in _SNIS_CODE_COLUMNS for value in norm_row):
            continue
        if not any(value in _SNIS_NAME_COLUMNS for value in norm_row):
            continue

        for offset in range(1, 6):
            candidate_idx = idx + offset
            if candidate_idx >= len(rows):
                break
            candidate_norm = [_normalize_column_name(cell) for cell in rows[candidate_idx]]
            if any(code in candidate_norm for code in normalized_indicators):
                header_idx = idx
                code_idx = candidate_idx
                header_norm = norm_row
                code_norm = candidate_norm
                break
        if header_idx is not None:
            break

    if header_idx is None or code_idx is None:
        return None

    header_row = rows[header_idx]
    ibge_col = next((idx for idx, value in enumerate(header_norm) if value in _SNIS_CODE_COLUMNS), None)
    municipality_col = next((idx for idx, value in enumerate(header_norm) if value in _SNIS_NAME_COLUMNS), None)
    if ibge_col is None or municipality_col is None:
        return None

    indicator_columns: dict[str, int] = {}
    for code in normalized_indicators:
        col_idx = next((idx for idx, value in enumerate(code_norm) if value == code), None)
        if col_idx is not None:
            indicator_columns[code] = col_idx
    if not indicator_columns:
        return None

    municipality_code_digits = _to_digits(municipality_ibge_code)
    municipality_name_norm = _normalize_text(municipality_name)
    code_prefix = municipality_code_digits[:6] if len(municipality_code_digits) >= 6 else municipality_code_digits

    for row in rows[code_idx + 1 :]:
        if not row:
            continue
        ibge_value = row[ibge_col] if ibge_col < len(row) else ''
        municipality_value = row[municipality_col] if municipality_col < len(row) else ''
        row_code = _to_digits(ibge_value)
        row_name_norm = _normalize_text(str(municipality_value))

        code_match = bool(row_code) and (
            row_code == municipality_code_digits or row_code.startswith(code_prefix)
        )
        name_match = row_name_norm == municipality_name_norm
        if not code_match and not name_match:
            continue

        extracted: dict[str, Any] = {
            'codigo_municipio': municipality_ibge_code,
            'municipio': municipality_name,
            'source_code_column': header_row[ibge_col] if ibge_col < len(header_row) else '',
        }
        found_any = False
        for code, field_name in normalized_indicators.items():
            col_idx = indicator_columns.get(code)
            if col_idx is None or col_idx >= len(row):
                continue
            raw_value = str(row[col_idx]).strip()
            if not raw_value:
                continue
            extracted[field_name] = _to_float_br(raw_value)
            found_any = True
        if found_any:
            return extracted
        return None

    return None


def _extract_snis_rs_metrics(
    rows: list[list[str]],
    *,
    municipality_ibge_code: str,
    municipality_name: str,
) -> dict[str, Any] | None:
    extracted = _extract_snis_indicator_metrics(
        rows,
        municipality_ibge_code=municipality_ibge_code,
        municipality_name=municipality_name,
        indicator_fields=SNIS_RS_INDICATOR_FIELDS,
    )
    if extracted is None:
        return None
    extracted['source_indicator_code'] = 'IN015'
    extracted['source_indicator_name'] = 'Tx cobertura da coleta RDO em relacao a pop. total'
    return extracted


def _xls_contains_municipality_hint(
    xls_bytes: bytes,
    *,
    municipality_ibge_code: str,
    municipality_name: str,
) -> bool:
    municipality_code = _to_digits(municipality_ibge_code)
    municipality_code6 = municipality_code[:6]
    payload = xls_bytes.decode('latin1', errors='ignore')
    if municipality_code and municipality_code in payload:
        return True
    if municipality_code6 and municipality_code6 in payload:
        return True
    return _normalize_text(municipality_name) in _normalize_text(payload)


def _convert_xls_bytes_to_xlsx_bytes_with_excel(
    xls_bytes: bytes,
    *,
    source_name: str,
) -> bytes:
    temp_root = RAW_DIR / "snis" / "_tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_dir = temp_root / f"snis_xls_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        source_path = temp_dir / source_name
        target_path = temp_dir / f"{source_path.stem}.xlsx"
        source_path.write_bytes(xls_bytes)

        source_ps = str(source_path.resolve()).replace("'", "''")
        target_ps = str(target_path.resolve()).replace("'", "''")
        script = "\n".join(
            [
                "$ErrorActionPreference = 'Stop'",
                '$excel = $null',
                '$workbook = $null',
                'try {',
                '  $excel = New-Object -ComObject Excel.Application',
                '  $excel.Visible = $false',
                '  $excel.DisplayAlerts = $false',
                f"  $workbook = $excel.Workbooks.Open('{source_ps}')",
                f"  $workbook.SaveAs('{target_ps}', 51)",
                '} finally {',
                '  if ($workbook -ne $null) {',
                '    $workbook.Close($false) | Out-Null',
                '    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($workbook)',
                '  }',
                '  if ($excel -ne $null) {',
                '    $excel.Quit()',
                '    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel)',
                '  }',
                '  [GC]::Collect()',
                '  [GC]::WaitForPendingFinalizers()',
                '}',
            ]
        )
        command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not target_path.exists():
            error_text = result.stderr.strip() or result.stdout.strip() or "Excel COM conversion failed."
            raise RuntimeError(error_text)
        return target_path.read_bytes()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _extract_snis_ae_metrics(
    session: requests.Session,
    *,
    requested_reference_year: str,
    municipality_name: str,
    municipality_ibge_code: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    details: dict[str, Any] = {
        'attempted_years': [],
        'attempted_files': [],
    }

    try:
        requested_year_int = int(str(requested_reference_year))
    except ValueError:
        requested_year_int = int(SNIS_RS_REFERENCE_YEAR)

    year_candidates = [str(requested_year_int - offset) for offset in range(0, SNIS_AE_YEARS_LOOKBACK + 1)]
    for year in year_candidates:
        details['attempted_years'].append(year)
        download_url = SNIS_AE_ZIP_URL_TEMPLATE.format(year=year)
        year_matches: list[dict[str, Any]] = []
        try:
            response = session.get(download_url, timeout=120)
            if response.status_code != 200:
                continue
            response.raise_for_status()
        except Exception:
            continue

        raw_path = RAW_DIR / 'snis' / Path(download_url).name
        raw_path.write_bytes(response.content)
        details['selected_ae_download_url'] = download_url
        details['selected_ae_raw_file'] = str(raw_path.relative_to(PROJECT_ROOT))

        try:
            outer_zip = zipfile.ZipFile(io.BytesIO(response.content))
        except Exception:
            continue

        nested_files = [name for name in outer_zip.namelist() if name.lower().endswith('.zip')]
        if not nested_files:
            continue

        def _nested_priority(name: str) -> tuple[int, str]:
            norm = _normalize_text(name)
            if 'completa_regionais' in norm:
                return (0, norm)
            if 'completa_microrregionais' in norm:
                return (1, norm)
            if 'completa_lpu' in norm:
                return (2, norm)
            return (3, norm)

        for nested_name in sorted(nested_files, key=_nested_priority):
            try:
                nested_zip = zipfile.ZipFile(io.BytesIO(outer_zip.read(nested_name)))
            except Exception:
                continue

            indicator_files = [
                file_name
                for file_name in nested_zip.namelist()
                if file_name.lower().endswith(('.xlsx', '.xls'))
                and 'indicadores' in _normalize_text(file_name)
            ]
            for indicator_file in sorted(indicator_files):
                details['attempted_files'].append(f'{nested_name}:{indicator_file}')
                try:
                    file_bytes = nested_zip.read(indicator_file)
                except Exception:
                    continue

                suffix = Path(indicator_file).suffix.casefold()
                if suffix == '.xlsx':
                    rows = _read_xlsx_rows(file_bytes, preferred_sheet='Indicadores')
                elif suffix == '.xls':
                    if not _xls_contains_municipality_hint(
                        file_bytes,
                        municipality_ibge_code=municipality_ibge_code,
                        municipality_name=municipality_name,
                    ):
                        continue
                    try:
                        converted_bytes = _convert_xls_bytes_to_xlsx_bytes_with_excel(
                            file_bytes,
                            source_name=Path(indicator_file).name,
                        )
                    except Exception as exc:
                        details['xls_conversion_error'] = str(exc)
                        continue
                    rows = _read_xlsx_rows(converted_bytes, preferred_sheet='Indicadores')
                else:
                    continue

                extracted = _extract_snis_indicator_metrics(
                    rows,
                    municipality_ibge_code=municipality_ibge_code,
                    municipality_name=municipality_name,
                    indicator_fields=SNIS_AE_INDICATOR_FIELDS,
                )
                if extracted is None:
                    continue
                extracted['dataset_reference_year'] = year
                extracted['download_url'] = download_url
                extracted['source_file'] = f'{nested_name}:{indicator_file}'
                year_matches.append(extracted)

        if year_matches:
            def _score(match: dict[str, Any]) -> tuple[int, float, float, float]:
                water = match.get('atendimento_agua_percentual')
                sewage = match.get('atendimento_esgoto_percentual')
                losses = match.get('perdas_agua_percentual')
                present = int(water is not None) + int(sewage is not None) + int(losses is not None)
                return (
                    present,
                    float(water or -1),
                    float(sewage or -1),
                    float(losses or -1),
                )

            details['year_match_count'] = len(year_matches)
            best_match = sorted(year_matches, key=_score, reverse=True)[0]
            return best_match, details

    return None, details


def _session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


def _load_catalog_resources(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    resources = payload.get("resources", [])
    if not isinstance(resources, list):
        return []
    return [item for item in resources if isinstance(item, dict)]


def _extract_tabular_from_zip(
    raw_bytes: bytes,
    *,
    preferred_names: tuple[str, ...] | None = None,
) -> tuple[bytes, str, str]:
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
        candidates = [
            name
            for name in archive.namelist()
            if Path(name).suffix.casefold() in {".csv", ".txt", ".xlsx", ".xls", ".json"}
        ]
        if not candidates:
            raise ValueError("ZIP has no supported tabular file.")
        selected: str | None = None
        normalized_preferences = tuple(
            _normalize_text(str(token))
            for token in (preferred_names or ())
            if str(token).strip()
        )
        if normalized_preferences:
            for candidate in sorted(candidates):
                normalized_candidate = _normalize_text(Path(candidate).stem)
                if any(token in normalized_candidate for token in normalized_preferences):
                    selected = candidate
                    break
        if selected is None:
            selected = sorted(candidates)[0]
        return archive.read(selected), Path(selected).suffix.casefold(), selected


def _parse_float_any(value: Any) -> float | None:
    token = str(value or "").strip()
    if not token:
        return None
    token = token.replace("%", "").replace("R$", "").replace(" ", "")
    if "," in token and "." in token:
        token = token.replace(".", "").replace(",", ".")
    else:
        token = token.replace(",", ".")
    token = re.sub(r"[^0-9.-]", "", token)
    if not token or token in {"-", ".", "-."}:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def _load_tabular_dataframe(
    raw_bytes: bytes,
    suffix: str,
    *,
    source_name: str | None = None,
    preferred_zip_entry_names: tuple[str, ...] | None = None,
) -> tuple[pd.DataFrame, str | None]:
    normalized_suffix = suffix.casefold()
    if normalized_suffix == ".zip":
        inner_bytes, inner_suffix, inner_name = _extract_tabular_from_zip(
            raw_bytes,
            preferred_names=preferred_zip_entry_names,
        )
        return _load_tabular_dataframe(inner_bytes, inner_suffix, source_name=inner_name)
    if normalized_suffix in {".csv", ".txt"}:
        best_df: pd.DataFrame | None = None
        best_score: tuple[int, int] = (-1, -1)

        for encoding in ("utf-8", "latin1"):
            text_preview = raw_bytes.decode(encoding, errors="replace")
            lines = text_preview.splitlines()
            for idx, line in enumerate(lines):
                normalized = _normalize_text(line)
                if normalized.startswith("data;hora"):
                    try:
                        inmet_df = pd.read_csv(
                            io.BytesIO(raw_bytes),
                            encoding=encoding,
                            sep=";",
                            skiprows=idx,
                            low_memory=False,
                        )
                        score = (len(inmet_df.columns), int(len(inmet_df)))
                        if score > best_score:
                            best_df = inmet_df
                            best_score = score
                    except Exception:
                        pass
                    break

            for sep in (";", ",", "\t", "|"):
                try:
                    df = pd.read_csv(io.BytesIO(raw_bytes), encoding=encoding, sep=sep, low_memory=False)
                except Exception:
                    continue
                score = (len(df.columns), int(len(df)))
                if score > best_score:
                    best_df = df
                    best_score = score
        if best_df is None:
            raise ValueError("Could not parse CSV/TXT payload.")
        return best_df, source_name
    if normalized_suffix in {".xlsx", ".xls"}:
        return pd.read_excel(io.BytesIO(raw_bytes)), source_name
    if normalized_suffix == ".json":
        payload = json.loads(raw_bytes.decode("utf-8"))
        if isinstance(payload, list):
            return pd.DataFrame(payload), source_name
        if isinstance(payload, dict):
            result_payload = payload.get("result")
            if isinstance(result_payload, dict) and isinstance(result_payload.get("records"), list):
                return pd.DataFrame(result_payload["records"]), source_name
            if isinstance(payload.get("records"), list):
                return pd.DataFrame(payload["records"]), source_name
            return pd.DataFrame([payload]), source_name
        raise ValueError("Unsupported JSON payload.")
    raise ValueError(f"Unsupported suffix '{suffix}'.")


def _resolve_municipality_subset(
    df: pd.DataFrame,
    *,
    municipality_ibge_code: str,
    municipality_name: str,
    source_file_name: str | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df
    normalized_df = df.rename(columns={col: _normalize_column_name(str(col)) for col in df.columns})
    target_name = _normalize_text(municipality_name)
    code_candidates = {municipality_ibge_code, municipality_ibge_code[:6]}

    code_columns = (
        "municipio_ibge",
        "codigo_municipio",
        "cod_municipio",
        "cdmun",
        "codmunres",
        "codigo_ibge",
        "codigo_ibge_7",
        "cod_ibge",
        "ibge",
        "id_municipio",
        "codmunicipioibge",
    )
    name_columns = ("municipio", "nome_municipio", "nm_municipio", "nmmun", "cidade", "localidade")

    has_code_columns = any(column in normalized_df.columns for column in code_columns)
    has_name_columns = any(column in normalized_df.columns for column in name_columns)
    mask = []
    for _, row in normalized_df.iterrows():
        code_match = False
        for column in code_columns:
            if column not in normalized_df.columns:
                continue
            if _to_digits(row.get(column)) in code_candidates:
                code_match = True
                break

        name_match = False
        if not code_match:
            for column in name_columns:
                if column not in normalized_df.columns:
                    continue
                row_name = _normalize_text(str(row.get(column, "")))
                if row_name == target_name or target_name in row_name:
                    name_match = True
                    break

        mask.append(code_match or name_match)

    matched = normalized_df.loc[mask].copy()
    if not matched.empty:
        return matched

    if (
        source_file_name
        and not has_code_columns
        and not has_name_columns
        and target_name
        and target_name in _normalize_text(Path(source_file_name).stem)
    ):
        return normalized_df.copy()

    return matched


def _filter_rows_by_reference_year(
    rows: pd.DataFrame,
    *,
    reference_year: str,
    year_columns: list[str] | tuple[str, ...] | None,
) -> pd.DataFrame:
    if rows.empty or not year_columns:
        return rows
    normalized_year_columns = [_normalize_column_name(str(col)) for col in year_columns if str(col).strip()]
    if not normalized_year_columns:
        return rows

    def _matches_year(value: Any) -> bool:
        token = str(value or "").strip()
        if not token:
            return False
        digits = _to_digits(token)
        if len(digits) >= 4 and digits[:4] == reference_year:
            return True
        return token.startswith(reference_year)

    mask: list[bool] = []
    for _, row in rows.iterrows():
        row_match = False
        for column in normalized_year_columns:
            if column not in rows.columns:
                continue
            if _matches_year(row.get(column)):
                row_match = True
                break
        mask.append(row_match)

    filtered = rows.loc[mask].copy()
    return filtered if not filtered.empty else rows


def _aggregate_metric_from_rows(
    rows: pd.DataFrame,
    *,
    aliases: list[str],
    mode: str,
    filters: dict[str, list[str] | tuple[str, ...]] | None = None,
) -> float | None:
    if rows.empty:
        return None
    normalized_rows = rows.rename(columns={col: _normalize_column_name(str(col)) for col in rows.columns})
    filtered_rows = normalized_rows
    if filters:
        normalized_filters = {
            _normalize_column_name(str(column)): tuple(
                _normalize_text(str(item))
                for item in values
                if str(item).strip()
            )
            for column, values in filters.items()
        }
        mask: list[bool] = []
        for _, row in normalized_rows.iterrows():
            row_ok = True
            for column, allowed_values in normalized_filters.items():
                if not allowed_values:
                    continue
                if column not in normalized_rows.columns:
                    row_ok = False
                    break
                row_value = _normalize_text(str(row.get(column, "")))
                if not any(item == row_value or item in row_value for item in allowed_values):
                    row_ok = False
                    break
            mask.append(row_ok)
        filtered_rows = normalized_rows.loc[mask].copy()

    if filtered_rows.empty:
        return None

    normalized_aliases = [_normalize_column_name(alias) for alias in aliases]
    if mode == "count":
        if not normalized_aliases:
            return float(len(filtered_rows))
        count = 0
        for _, row in filtered_rows.iterrows():
            for alias in normalized_aliases:
                if alias not in filtered_rows.columns:
                    continue
                value = str(row.get(alias, "")).strip()
                if value:
                    count += 1
                    break
        return float(count)

    values: list[float] = []
    for _, row in filtered_rows.iterrows():
        for alias in normalized_aliases:
            if alias not in filtered_rows.columns:
                continue
            parsed = _parse_float_any(row.get(alias))
            if parsed is not None:
                values.append(parsed)
                break
    if not values:
        return None
    if mode == "sum":
        return float(sum(values))
    if mode == "avg":
        return float(sum(values) / len(values))
    if mode == "max":
        return float(max(values))
    if mode == "min":
        return float(min(values))
    if mode == "first":
        return float(values[0])
    raise ValueError(f"Unsupported metric mode '{mode}'.")


def _bootstrap_tabular_catalog_source(
    *,
    source: str,
    catalog_path: Path,
    raw_subdir: str,
    manual_subdir: str,
    output_filename: str,
    reference_year: str,
    municipality_name: str,
    municipality_ibge_code: str,
    metric_specs: list[dict[str, Any]],
    reference_year_columns: list[str] | tuple[str, ...] | None = None,
) -> SourceResult:
    session = _session()
    resources = _load_catalog_resources(catalog_path)
    if not resources:
        return SourceResult(
            source=source,
            status="manual_required",
            details={
                "reason": f"No catalog resources configured in {catalog_path.name}.",
                "catalog_path": str(catalog_path.relative_to(PROJECT_ROOT)),
            },
        )

    attempts: list[dict[str, Any]] = []
    municipality_ibge_code_6 = (
        municipality_ibge_code[:6] if len(municipality_ibge_code) >= 6 else municipality_ibge_code
    )
    for resource in resources:
        uri_template = str(resource.get("uri", "")).strip()
        if not uri_template:
            continue
        uri = uri_template.format(
            reference_period=reference_year,
            municipality_ibge_code=municipality_ibge_code,
            municipality_ibge_code_6=municipality_ibge_code_6,
        )
        suffix = str(resource.get("extension", "")).strip().casefold() or Path(uri).suffix.casefold()
        try:
            response = session.get(uri, timeout=120)
            response.raise_for_status()
            raw_bytes = response.content
            parsed_uri = urlparse(uri)
            raw_filename = Path(parsed_uri.path).name or f"{source.casefold()}_{reference_year}{suffix or '.dat'}"
            if Path(raw_filename).suffix == "" and suffix:
                raw_filename = f"{raw_filename}{suffix}"
            raw_path = RAW_DIR / raw_subdir / raw_filename
            raw_path.write_bytes(raw_bytes)

            dataframe, parsed_source_name = _load_tabular_dataframe(
                raw_bytes,
                suffix=suffix or ".csv",
                source_name=raw_filename,
                preferred_zip_entry_names=(
                    municipality_name,
                    municipality_ibge_code,
                    municipality_ibge_code[:6],
                ),
            )
            municipality_rows = _resolve_municipality_subset(
                dataframe,
                municipality_ibge_code=municipality_ibge_code,
                municipality_name=municipality_name,
                source_file_name=parsed_source_name or raw_filename,
            )
            municipality_rows = _filter_rows_by_reference_year(
                municipality_rows,
                reference_year=reference_year,
                year_columns=reference_year_columns,
            )
            if municipality_rows.empty:
                attempts.append(
                    {
                        "uri": uri,
                        "status": "municipality_not_found",
                        "raw_file": str(raw_path.relative_to(PROJECT_ROOT)),
                    }
                )
                continue

            output_row: dict[str, Any] = {
                "codigo_municipio": municipality_ibge_code,
                "municipio": municipality_name,
            }
            metrics_found = 0
            for spec in metric_specs:
                value = _aggregate_metric_from_rows(
                    municipality_rows,
                    aliases=[str(alias) for alias in spec.get("aliases", [])],
                    mode=str(spec.get("mode", "sum")),
                    filters=(
                        {
                            str(k): tuple(str(item) for item in values)
                            for k, values in dict(spec.get("filters", {})).items()
                        }
                        if isinstance(spec.get("filters"), dict)
                        else None
                    ),
                )
                if value is None:
                    continue
                output_row[str(spec["column"])] = value
                metrics_found += 1

            if metrics_found == 0:
                attempts.append(
                    {
                        "uri": uri,
                        "status": "metrics_not_found",
                        "raw_file": str(raw_path.relative_to(PROJECT_ROOT)),
                        "columns": list(municipality_rows.columns),
                    }
                )
                continue

            output_path = MANUAL_DIR / manual_subdir / output_filename
            pd.DataFrame([output_row]).to_csv(output_path, index=False, sep=";")
            return SourceResult(
                source=source,
                status="ok",
                output_file=str(output_path.relative_to(PROJECT_ROOT)),
                details={
                    "download_url": uri,
                    "raw_file": str(raw_path.relative_to(PROJECT_ROOT)),
                    "rows_matched": int(len(municipality_rows)),
                    "metrics_found": metrics_found,
                },
            )
        except Exception as exc:
            attempts.append({"uri": uri, "status": "error", "error": str(exc)})

    return SourceResult(
        source=source,
        status="manual_required",
        details={
            "reason": "Could not produce municipal CSV from configured catalog resources.",
            "catalog_path": str(catalog_path.relative_to(PROJECT_ROOT)),
            "attempts": attempts[-5:],
        },
    )


def _ensure_dirs() -> None:
    for path in (
        MANUAL_DIR / "mte",
        MANUAL_DIR / "senatran",
        MANUAL_DIR / "sejusp",
        MANUAL_DIR / "siops",
        MANUAL_DIR / "snis",
        MANUAL_DIR / "inmet",
        MANUAL_DIR / "inpe_queimadas",
        MANUAL_DIR / "ana",
        MANUAL_DIR / "anatel",
        MANUAL_DIR / "aneel",
        RAW_DIR / "mte",
        RAW_DIR / "senatran",
        RAW_DIR / "sejusp",
        RAW_DIR / "siops",
        RAW_DIR / "snis",
        RAW_DIR / "inmet",
        RAW_DIR / "inpe_queimadas",
        RAW_DIR / "ana",
        RAW_DIR / "anatel",
        RAW_DIR / "aneel",
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


def bootstrap_snis(
    reference_year: str,
    municipality_name: str,
    municipality_ibge_code: str,
) -> SourceResult:
    source = "SNIS"
    try:
        session = _session()
        raw_zip_path = RAW_DIR / "snis" / Path(SNIS_RS_ZIP_URL).name
        response = session.get(SNIS_RS_ZIP_URL, timeout=120)
        response.raise_for_status()
        raw_zip_path.write_bytes(response.content)

        indicators_xlsx_path = RAW_DIR / "snis" / SNIS_RS_INDICATORS_FILE
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            members = archive.namelist()
            selected = SNIS_RS_INDICATORS_FILE if SNIS_RS_INDICATORS_FILE in members else None
            if selected is None:
                preferred = [
                    name
                    for name in members
                    if name.lower().endswith(".xlsx") and "indicadores_rs" in _normalize_text(name)
                ]
                selected = preferred[0] if preferred else None
            if selected is None:
                preferred = [name for name in members if name.lower().endswith(".xlsx")]
                selected = preferred[0] if preferred else None
            if selected is None:
                return SourceResult(
                    source=source,
                    status="manual_required",
                    details={
                        "reason": "SNIS RS ZIP does not contain an XLSX indicators file.",
                        "download_url": SNIS_RS_ZIP_URL,
                        "raw_file": str(raw_zip_path.relative_to(PROJECT_ROOT)),
                    },
                )
            indicators_bytes = archive.read(selected)
            indicators_xlsx_path.write_bytes(indicators_bytes)

        rows = _read_xlsx_rows(indicators_bytes, preferred_sheet="Indicadores")
        extracted_rs = _extract_snis_rs_metrics(
            rows,
            municipality_ibge_code=municipality_ibge_code,
            municipality_name=municipality_name,
        )
        extracted_ae, ae_details = _extract_snis_ae_metrics(
            session,
            requested_reference_year=reference_year,
            municipality_name=municipality_name,
            municipality_ibge_code=municipality_ibge_code,
        )

        if extracted_rs is None and extracted_ae is None:
            return SourceResult(
                source=source,
                status="manual_required",
                details={
                    "reason": "Could not locate SNIS municipality metrics in RS/AE datasets.",
                    "rs_download_url": SNIS_RS_ZIP_URL,
                    "rs_raw_file": str(raw_zip_path.relative_to(PROJECT_ROOT)),
                    "rs_xlsx_file": str(indicators_xlsx_path.relative_to(PROJECT_ROOT)),
                    "ae_attempted_years": ae_details.get("attempted_years", []),
                },
            )

        atendimento_agua_percentual = (
            extracted_ae.get("atendimento_agua_percentual")
            if extracted_ae is not None
            else None
        )
        atendimento_esgoto_percentual = (
            extracted_ae.get("atendimento_esgoto_percentual")
            if extracted_ae is not None
            else None
        )
        perdas_agua_percentual = (
            extracted_ae.get("perdas_agua_percentual")
            if extracted_ae is not None
            else None
        )
        coleta_residuos_percentual = (
            extracted_rs.get("coleta_residuos_percentual")
            if extracted_rs is not None
            else None
        )

        output_path = MANUAL_DIR / "snis" / f"snis_diamantina_{reference_year}.csv"
        pd.DataFrame(
            [
                {
                    "codigo_municipio": municipality_ibge_code,
                    "municipio": municipality_name,
                    "atendimento_agua_percentual": (
                        "" if atendimento_agua_percentual is None else atendimento_agua_percentual
                    ),
                    "atendimento_esgoto_percentual": (
                        "" if atendimento_esgoto_percentual is None else atendimento_esgoto_percentual
                    ),
                    "perdas_agua_percentual": (
                        "" if perdas_agua_percentual is None else perdas_agua_percentual
                    ),
                    "coleta_residuos_percentual": (
                        "" if coleta_residuos_percentual is None else coleta_residuos_percentual
                    ),
                }
            ]
        ).to_csv(output_path, index=False, sep=";")

        missing_codes: list[str] = []
        if atendimento_agua_percentual is None:
            missing_codes.append("IN055")
        if atendimento_esgoto_percentual is None:
            missing_codes.append("IN056")
        if perdas_agua_percentual is None:
            missing_codes.append("IN049")
        if coleta_residuos_percentual is None:
            missing_codes.append("IN015")

        return SourceResult(
            source=source,
            status="ok",
            output_file=str(output_path.relative_to(PROJECT_ROOT)),
            details={
                "rs_download_url": SNIS_RS_ZIP_URL,
                "rs_dataset_reference_year": SNIS_RS_REFERENCE_YEAR,
                "requested_reference_year": reference_year,
                "rs_raw_file": str(raw_zip_path.relative_to(PROJECT_ROOT)),
                "rs_xlsx_file": str(indicators_xlsx_path.relative_to(PROJECT_ROOT)),
                "rs_source_indicator_code": "IN015",
                "ae_selected_download_url": ae_details.get("selected_ae_download_url"),
                "ae_selected_raw_file": ae_details.get("selected_ae_raw_file"),
                "ae_attempted_years": ae_details.get("attempted_years", []),
                "ae_attempted_files_count": len(ae_details.get("attempted_files", [])),
                "ae_year_match_count": ae_details.get("year_match_count"),
                "ae_xls_conversion_error": ae_details.get("xls_conversion_error"),
                "ae_dataset_reference_year": (
                    extracted_ae.get("dataset_reference_year") if extracted_ae is not None else None
                ),
                "ae_source_file": extracted_ae.get("source_file") if extracted_ae is not None else None,
                "missing_indicator_codes": missing_codes,
            },
        )
    except Exception as exc:
        return SourceResult(source=source, status="error", error=str(exc))


def bootstrap_inmet(
    reference_year: str,
    municipality_name: str,
    municipality_ibge_code: str,
) -> SourceResult:
    return _bootstrap_tabular_catalog_source(
        source="INMET",
        catalog_path=INMET_CATALOG_PATH,
        raw_subdir="inmet",
        manual_subdir="inmet",
        output_filename=f"inmet_diamantina_{reference_year}.csv",
        reference_year=reference_year,
        municipality_name=municipality_name,
        municipality_ibge_code=municipality_ibge_code,
        metric_specs=[
            {
                "column": "precipitacao_total_mm",
                "aliases": [
                    "precipitacao_total_mm",
                    "precipitacao_total_horario_mm",
                    "precipitacao_mm",
                    "chuva_mm",
                    "precipitacao",
                ],
                "mode": "sum",
            },
            {
                "column": "temperatura_media_c",
                "aliases": [
                    "temperatura_media_c",
                    "temperatura_media",
                    "temp_media",
                    "temperatura_do_ar_bulbo_seco_horaria_c",
                ],
                "mode": "avg",
            },
            {
                "column": "umidade_relativa_media_percent",
                "aliases": [
                    "umidade_relativa_media_percent",
                    "umidade_media",
                    "ur_media",
                    "umidade_relativa_do_ar_horaria",
                    "umidade_relativa_do_ar_horaria_percentual",
                ],
                "mode": "avg",
            },
        ],
    )


def bootstrap_inpe_queimadas(
    reference_year: str,
    municipality_name: str,
    municipality_ibge_code: str,
) -> SourceResult:
    return _bootstrap_tabular_catalog_source(
        source="INPE_QUEIMADAS",
        catalog_path=INPE_QUEIMADAS_CATALOG_PATH,
        raw_subdir="inpe_queimadas",
        manual_subdir="inpe_queimadas",
        output_filename=f"inpe_queimadas_diamantina_{reference_year}.csv",
        reference_year=reference_year,
        municipality_name=municipality_name,
        municipality_ibge_code=municipality_ibge_code,
        metric_specs=[
            {
                "column": "focos_total",
                "aliases": ["focos_total", "focos", "numero_focos", "qtd_focos", "foco_id", "id_bdq"],
                "mode": "count",
            },
            {
                "column": "area_queimada_ha",
                "aliases": ["area_queimada_ha", "area_queimada", "area_ha"],
                "mode": "sum",
            },
            {
                "column": "risco_fogo_indice",
                "aliases": ["risco_fogo_indice", "risco_fogo", "indice_risco"],
                "mode": "max",
            },
        ],
    )


def bootstrap_ana(
    reference_year: str,
    municipality_name: str,
    municipality_ibge_code: str,
) -> SourceResult:
    return _bootstrap_tabular_catalog_source(
        source="ANA",
        catalog_path=ANA_CATALOG_PATH,
        raw_subdir="ana",
        manual_subdir="ana",
        output_filename=f"ana_diamantina_{reference_year}.csv",
        reference_year=reference_year,
        municipality_name=municipality_name,
        municipality_ibge_code=municipality_ibge_code,
        metric_specs=[
            {
                "column": "precipitacao_total_mm",
                "aliases": ["precipitacao_total_mm", "precipitacao_mm", "chuva_mm", "precipitacao", "chuva"],
                "mode": "sum",
            },
            {
                "column": "vazao_media_m3s",
                "aliases": [
                    "vazao_media_m3s",
                    "vztotm3s",
                    "vazao_media",
                    "vazao",
                    "vazao_retirada_m3s",
                    "vazao_retirada",
                    "q_ret_m3s",
                    "qret_m3s",
                    "vazret_m3s",
                ],
                "mode": "avg",
            },
            {
                "column": "vazao_humana_m3s",
                "aliases": ["vazao_humana_m3s", "vzhurm3s", "vzhrum3s"],
                "mode": "avg",
            },
            {
                "column": "vazao_irrigacao_m3s",
                "aliases": ["vazao_irrigacao_m3s", "vzirrm3s"],
                "mode": "avg",
            },
            {
                "column": "nivel_medio_m",
                "aliases": ["nivel_medio_m", "nivel_medio", "nivel"],
                "mode": "avg",
            },
        ],
        reference_year_columns=("ano", "ano_ref", "anoindice", "datreferenciainformada"),
    )


def bootstrap_anatel(
    reference_year: str,
    municipality_name: str,
    municipality_ibge_code: str,
) -> SourceResult:
    return _bootstrap_tabular_catalog_source(
        source="ANATEL",
        catalog_path=ANATEL_CATALOG_PATH,
        raw_subdir="anatel",
        manual_subdir="anatel",
        output_filename=f"anatel_diamantina_{reference_year}.csv",
        reference_year=reference_year,
        municipality_name=municipality_name,
        municipality_ibge_code=municipality_ibge_code,
        metric_specs=[
            {
                "column": "acessos_banda_larga_fixa",
                "aliases": ["acessos_banda_larga_fixa", "acessos_scm", "acessos_fixos", "acessos"],
                "mode": "sum",
                "filters": {"servico": ("banda larga fixa",)},
            },
            {
                "column": "acessos_banda_larga_movel",
                "aliases": ["acessos_banda_larga_movel", "acessos_smp_dados", "acessos_moveis", "acessos"],
                "mode": "sum",
                "filters": {"servico": ("telefonia movel", "banda larga movel")},
            },
            {
                "column": "densidade_banda_larga_fixa_100hab",
                "aliases": ["densidade_banda_larga_fixa_100hab", "densidade_100hab", "densidade"],
                "mode": "avg",
                "filters": {"servico": ("banda larga fixa",)},
            },
        ],
        reference_year_columns=("ano",),
    )


def bootstrap_aneel(
    reference_year: str,
    municipality_name: str,
    municipality_ibge_code: str,
) -> SourceResult:
    return _bootstrap_tabular_catalog_source(
        source="ANEEL",
        catalog_path=ANEEL_CATALOG_PATH,
        raw_subdir="aneel",
        manual_subdir="aneel",
        output_filename=f"aneel_diamantina_{reference_year}.csv",
        reference_year=reference_year,
        municipality_name=municipality_name,
        municipality_ibge_code=municipality_ibge_code,
        metric_specs=[
            {
                "column": "consumo_total_mwh",
                "aliases": ["consumo_total_mwh", "consumo_mwh", "energia_consumida_mwh", "consumo"],
                "mode": "sum",
            },
            {
                "column": "unidades_consumidoras_total",
                "aliases": ["unidades_consumidoras_total", "uc_total", "unidades_consumidoras", "uc", "qtducativa"],
                "mode": "sum",
            },
            {
                "column": "dic_medio_horas",
                "aliases": ["dic_medio_horas", "dic_horas", "dic", "dec"],
                "mode": "avg",
            },
        ],
        reference_year_columns=("datreferenciainformada", "anoindice"),
    )


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
    parser.add_argument("--skip-snis", action="store_true")
    parser.add_argument("--skip-snis-probe", action="store_true", dest="skip_snis")
    parser.add_argument("--skip-inmet", action="store_true")
    parser.add_argument("--skip-inpe-queimadas", action="store_true")
    parser.add_argument("--skip-ana", action="store_true")
    parser.add_argument("--skip-anatel", action="store_true")
    parser.add_argument("--skip-aneel", action="store_true")
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
    if not args.skip_snis:
        results.append(
            bootstrap_snis(
                reference_year=args.reference_year,
                municipality_name=args.municipality_name,
                municipality_ibge_code=args.municipality_ibge_code,
            )
        )
    if not args.skip_inmet:
        results.append(
            bootstrap_inmet(
                reference_year=args.reference_year,
                municipality_name=args.municipality_name,
                municipality_ibge_code=args.municipality_ibge_code,
            )
        )
    if not args.skip_inpe_queimadas:
        results.append(
            bootstrap_inpe_queimadas(
                reference_year=args.reference_year,
                municipality_name=args.municipality_name,
                municipality_ibge_code=args.municipality_ibge_code,
            )
        )
    if not args.skip_ana:
        results.append(
            bootstrap_ana(
                reference_year=args.reference_year,
                municipality_name=args.municipality_name,
                municipality_ibge_code=args.municipality_ibge_code,
            )
        )
    if not args.skip_anatel:
        results.append(
            bootstrap_anatel(
                reference_year=args.reference_year,
                municipality_name=args.municipality_name,
                municipality_ibge_code=args.municipality_ibge_code,
            )
        )
    if not args.skip_aneel:
        results.append(
            bootstrap_aneel(
                reference_year=args.reference_year,
                municipality_name=args.municipality_name,
                municipality_ibge_code=args.municipality_ibge_code,
            )
        )

    report_path = Path(args.report_path)
    _dump_report(results, report_path)

    print(json.dumps({"report_path": str(report_path), "results": [r.__dict__ for r in results]}, ensure_ascii=False, indent=2))
    has_error = any(result.status == "error" for result in results)
    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
