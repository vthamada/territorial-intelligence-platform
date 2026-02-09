from __future__ import annotations

import io
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run

JOB_NAME = "education_inep_fetch"
SOURCE = "INEP"
DATASET_NAME = "inep_sinopse_educacao_basica"
WAVE = "MVP-3"
SINOPSE_BASE_URL = (
    "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/"
    "sinopses-estatisticas/educacao-basica"
)

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _normalize_text(value: str) -> str:
    stripped = value.strip().casefold()
    return "".join(
        ch
        for ch in unicodedata.normalize("NFKD", stripped)
        if not unicodedata.combining(ch)
    )


def _parse_reference_year(reference_period: str) -> int:
    token = str(reference_period).strip()
    if not token:
        raise ValueError("reference_period is empty")
    year_token = token.split("-")[0]
    if not year_token.isdigit() or len(year_token) != 4:
        raise ValueError(f"Invalid reference_period '{reference_period}'. Expected year (YYYY).")
    return int(year_token)


def _extract_sinopse_zip_links(html: str) -> list[str]:
    links = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    selected: list[str] = []
    for link in links:
        token = link.strip()
        if not token:
            continue
        low = token.casefold()
        if not low.endswith(".zip"):
            continue
        if "download.inep.gov.br" not in low:
            continue
        if "sinopse" not in low:
            continue
        if "educacao_basica" not in low and "censo_escolar" not in low:
            continue
        selected.append(token)
    return sorted(set(selected), reverse=True)


def _extract_year_from_url(url: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", url)
    if match is None:
        return None
    return int(match.group(0))


def _choose_sinopse_zip(urls: list[str], requested_year: int) -> tuple[str, int | None, str | None]:
    if not urls:
        raise ValueError("No INEP sinopse ZIP links found.")

    ranked: list[tuple[str, int | None]] = [(url, _extract_year_from_url(url)) for url in urls]
    exact = [item for item in ranked if item[1] == requested_year]
    if exact:
        return exact[0][0], requested_year, None

    years = [year for _, year in ranked if year is not None]
    if years:
        candidates = [year for year in years if year <= requested_year]
        if candidates:
            selected_year = max(candidates)
        else:
            selected_year = max(years)
        for url, year in ranked:
            if year == selected_year:
                return (
                    url,
                    year,
                    (
                        f"Requested year {requested_year} not found; "
                        f"using nearest available year {selected_year}."
                    ),
                )

    return (
        ranked[0][0],
        None,
        f"Requested year {requested_year} not found; using first available ZIP.",
    )


def _parse_numeric(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Decimal(str(value))

    token = str(value).strip()
    if not token:
        return None
    normalized = token.replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _resolve_municipality_context(settings: Settings) -> tuple[str, str, str]:
    with session_scope(settings) as session:
        row = session.execute(
            text(
                """
                SELECT territory_id::text, name, municipality_ibge_code
                FROM silver.dim_territory
                WHERE level = 'municipality'
                  AND municipality_ibge_code = :municipality_ibge_code
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """
            ),
            {"municipality_ibge_code": settings.municipality_ibge_code},
        ).first()

    if row is None:
        raise RuntimeError("Municipality territory not found. Run ibge_admin_fetch first.")
    territory_id = str(row[0]).strip()
    municipality_name = str(row[1]).strip()
    municipality_ibge_code = str(row[2]).strip()
    if not territory_id or not municipality_name or not municipality_ibge_code:
        raise RuntimeError("Invalid municipality context in dim_territory.")
    return territory_id, municipality_name, municipality_ibge_code


def _load_shared_strings(xlsx_zip: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in xlsx_zip.namelist():
        return []

    shared: list[str] = []
    for _event, elem in ET.iterparse(
        io.BytesIO(xlsx_zip.read("xl/sharedStrings.xml")),
        events=("end",),
    ):
        if elem.tag != _NS + "si":
            continue
        texts = [node.text or "" for node in elem.iter(_NS + "t")]
        shared.append("".join(texts))
        elem.clear()
    return shared


def _resolve_sheet_path(xlsx_zip: zipfile.ZipFile) -> str:
    rels: dict[str, str] = {}
    for _event, elem in ET.iterparse(
        io.BytesIO(xlsx_zip.read("xl/_rels/workbook.xml.rels")),
        events=("end",),
    ):
        if elem.tag != _REL_NS + "Relationship":
            continue
        rel_id = elem.attrib.get("Id")
        target = elem.attrib.get("Target")
        if rel_id and target:
            rels[rel_id] = f"xl/{target}"
        elem.clear()

    candidates: list[tuple[str, str]] = []
    for _event, elem in ET.iterparse(io.BytesIO(xlsx_zip.read("xl/workbook.xml")), events=("end",)):
        if elem.tag != _NS + "sheet":
            continue
        name = elem.attrib.get("name", "")
        rel_id = elem.attrib.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id",
            "",
        )
        target = rels.get(rel_id)
        if target:
            candidates.append((name, target))
        elem.clear()

    normalized_candidates = [(_normalize_text(name), target) for name, target in candidates]
    for name, target in normalized_candidates:
        if "educacao basica 1.1" in name:
            return target
    for name, target in normalized_candidates:
        if "1.1" in name:
            return target
    if candidates:
        return candidates[0][1]
    raise ValueError("No worksheet found in INEP workbook.")


def _iter_sheet_rows(
    xlsx_zip: zipfile.ZipFile,
    *,
    sheet_path: str,
    shared_strings: list[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for _event, elem in ET.iterparse(io.BytesIO(xlsx_zip.read(sheet_path)), events=("end",)):
        if elem.tag != _NS + "row":
            continue
        parsed_row: dict[str, str] = {}
        for cell in elem.findall(_NS + "c"):
            ref = cell.attrib.get("r", "")
            column = "".join(ch for ch in ref if ch.isalpha())
            value_node = cell.find(_NS + "v")
            if not column or value_node is None:
                continue
            raw_value = value_node.text or ""
            if cell.attrib.get("t") == "s":
                index = int(raw_value) if raw_value.isdigit() else -1
                if 0 <= index < len(shared_strings):
                    parsed_row[column] = shared_strings[index]
                else:
                    parsed_row[column] = raw_value
            else:
                parsed_row[column] = raw_value
        if parsed_row:
            rows.append(parsed_row)
        elem.clear()
    return rows


def _find_municipality_row(
    rows: list[dict[str, str]],
    *,
    municipality_name: str,
    municipality_ibge_code: str,
) -> dict[str, str] | None:
    target_name = _normalize_text(municipality_name)
    code_candidates = {municipality_ibge_code}
    if len(municipality_ibge_code) >= 6:
        code_candidates.add(municipality_ibge_code[:6])

    by_code = [
        row
        for row in rows
        if str(row.get("D", "")).strip() in code_candidates
    ]
    if by_code:
        return by_code[0]

    by_name = [
        row
        for row in rows
        if _normalize_text(str(row.get("C", ""))) == target_name
    ]
    if by_name:
        return by_name[0]
    return None


def _build_indicator_rows(
    *,
    territory_id: str,
    row: dict[str, str],
    reference_period: str,
) -> list[dict[str, Any]]:
    total = _parse_numeric(row.get("E"))
    if total is None:
        raise ValueError("Could not parse total enrolments from INEP row (column E).")

    return [
        {
            "territory_id": territory_id,
            "source": SOURCE,
            "dataset": DATASET_NAME,
            "indicator_code": "INEP_CENSO_ESCOLAR_MATRICULAS_TOTAL",
            "indicator_name": "INEP Censo Escolar matriculas totais",
            "unit": "count",
            "category": "sinopse_educacao_basica_1_1",
            "value": total,
            "reference_period": reference_period,
        }
    ]


def run(
    *,
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
    settings: Settings | None = None,
) -> dict[str, Any]:
    del force
    settings = settings or get_settings()
    logger = get_logger(JOB_NAME)
    run_id = str(uuid4())
    started_at_utc = datetime.now(UTC)
    started_at = time.perf_counter()
    warnings: list[str] = []

    try:
        requested_year = _parse_reference_year(reference_period)
    except ValueError as exc:
        return {
            "job": JOB_NAME,
            "status": "failed",
            "run_id": run_id,
            "duration_seconds": 0.0,
            "rows_extracted": 0,
            "rows_written": 0,
            "warnings": warnings,
            "errors": [str(exc)],
        }

    client = HttpClient.from_settings(
        settings,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    try:
        territory_id, municipality_name, municipality_ibge_code = _resolve_municipality_context(
            settings
        )
        listing_response = client._request("GET", SINOPSE_BASE_URL)  # noqa: SLF001
        listing_html = listing_response.text
        zip_links = _extract_sinopse_zip_links(listing_html)
        selected_url, effective_year, year_warning = _choose_sinopse_zip(zip_links, requested_year)
        if year_warning:
            warnings.append(year_warning)

        zip_bytes, _ = client.download_bytes(
            selected_url,
            expected_content_types=["zip", "octet-stream", "application/zip"],
            min_bytes=2048,
        )
        archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
        xlsx_candidates = [name for name in archive.namelist() if name.lower().endswith(".xlsx")]
        if not xlsx_candidates:
            raise RuntimeError("INEP ZIP has no XLSX file.")
        workbook_bytes = archive.read(xlsx_candidates[0])

        workbook_zip = zipfile.ZipFile(io.BytesIO(workbook_bytes))
        shared_strings = _load_shared_strings(workbook_zip)
        sheet_path = _resolve_sheet_path(workbook_zip)
        rows = _iter_sheet_rows(
            workbook_zip,
            sheet_path=sheet_path,
            shared_strings=shared_strings,
        )
        municipality_row = _find_municipality_row(
            rows,
            municipality_name=municipality_name,
            municipality_ibge_code=municipality_ibge_code,
        )
        if municipality_row is None:
            raise RuntimeError("Municipality row not found in INEP workbook.")

        effective_period = str(effective_year or requested_year)
        load_rows = _build_indicator_rows(
            territory_id=territory_id,
            row=municipality_row,
            reference_period=effective_period,
        )

        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": JOB_NAME,
                "status": "success",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": len(rows),
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "preview": {
                    "selected_url": selected_url,
                    "requested_year": requested_year,
                    "effective_period": effective_period,
                    "municipality_code_in_source": municipality_row.get("D"),
                    "municipality_name_in_source": municipality_row.get("C"),
                    "indicators": [
                        {
                            "indicator_code": row["indicator_code"],
                            "value": str(row["value"]),
                        }
                        for row in load_rows
                    ],
                },
            }

        rows_written = 0
        with session_scope(settings) as session:
            for row in load_rows:
                session.execute(
                    text(
                        """
                        INSERT INTO silver.fact_indicator (
                            territory_id,
                            source,
                            dataset,
                            indicator_code,
                            indicator_name,
                            unit,
                            category,
                            value,
                            reference_period
                        )
                        VALUES (
                            CAST(:territory_id AS uuid),
                            :source,
                            :dataset,
                            :indicator_code,
                            :indicator_name,
                            :unit,
                            :category,
                            :value,
                            :reference_period
                        )
                        ON CONFLICT (
                            territory_id,
                            source,
                            dataset,
                            indicator_code,
                            category,
                            reference_period
                        )
                        DO UPDATE SET
                            indicator_name = EXCLUDED.indicator_name,
                            unit = EXCLUDED.unit,
                            value = EXCLUDED.value,
                            updated_at = NOW()
                        """
                    ),
                    {
                        **row,
                        "value": str(row["value"]),
                    },
                )
                rows_written += 1

        checks = [
            {
                "name": "inep_zip_links_discovered",
                "status": "pass" if zip_links else "warn",
                "details": f"{len(zip_links)} INEP ZIP links discovered from listing page.",
                "observed_value": len(zip_links),
                "threshold_value": 1,
            },
            {
                "name": "inep_municipality_row_found",
                "status": "pass",
                "details": "Municipality row found in selected workbook.",
                "observed_value": 1,
                "threshold_value": 1,
            },
            {
                "name": "inep_indicators_loaded",
                "status": "pass" if rows_written > 0 else "warn",
                "details": f"{rows_written} indicators upserted into silver.fact_indicator.",
                "observed_value": rows_written,
                "threshold_value": 1,
            },
        ]

        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=effective_period,
            raw_bytes=zip_bytes,
            extension=".zip",
            uri=selected_url,
            territory_scope="municipality",
            dataset_version=f"sinopse-{effective_period}",
            checks=checks,
            notes="INEP sinopse educacao basica ZIP extraction and indicator upsert.",
            run_id=run_id,
            tables_written=["silver.fact_indicator"],
            rows_written=[{"table": "silver.fact_indicator", "rows": rows_written}],
        )

        finished_at_utc = datetime.now(UTC)
        with session_scope(settings) as session:
            upsert_pipeline_run(
                session=session,
                run_id=run_id,
                job_name=JOB_NAME,
                source=SOURCE,
                dataset=DATASET_NAME,
                wave=WAVE,
                reference_period=effective_period,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
                status="success",
                rows_extracted=len(rows),
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "selected_url": selected_url,
                    "requested_year": requested_year,
                    "effective_period": effective_period,
                    "municipality_code_in_source": municipality_row.get("D"),
                },
            )
            replace_pipeline_checks_from_dicts(
                session=session,
                run_id=run_id,
                checks=checks,
            )

        elapsed = time.perf_counter() - started_at
        logger.info(
            "INEP education job finished.",
            run_id=run_id,
            rows_extracted=len(rows),
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "success",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": len(rows),
            "rows_written": rows_written,
            "warnings": warnings,
            "errors": [],
            "bronze": artifact_to_dict(artifact),
        }
    except Exception as exc:  # pragma: no cover - runtime logging path
        elapsed = time.perf_counter() - started_at
        if not dry_run:
            try:
                with session_scope(settings) as session:
                    upsert_pipeline_run(
                        session=session,
                        run_id=run_id,
                        job_name=JOB_NAME,
                        source=SOURCE,
                        dataset=DATASET_NAME,
                        wave=WAVE,
                        reference_period=str(requested_year),
                        started_at_utc=started_at_utc,
                        finished_at_utc=datetime.now(UTC),
                        status="failed",
                        rows_extracted=0,
                        rows_loaded=0,
                        warnings_count=len(warnings),
                        errors_count=1,
                        details={"error": str(exc)},
                    )
            except Exception:
                logger.exception(
                    "Could not persist failed pipeline run in ops tables.",
                    run_id=run_id,
                )

        logger.exception(
            "INEP education job failed.",
            run_id=run_id,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "failed",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": 0,
            "rows_written": 0,
            "warnings": warnings,
            "errors": [str(exc)],
        }
    finally:
        client.close()
