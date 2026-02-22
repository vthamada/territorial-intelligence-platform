from __future__ import annotations

import io
import json
import math
import re
import time
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import pandas as pd
import yaml
from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run

_DEFAULT_MUNICIPALITY_CODE_COLUMNS = (
    "municipio_ibge",
    "codigo_municipio",
    "cod_municipio",
    "codmunres",
    "cod_ibge",
    "codigo_ibge",
    "codigo_ibge_7",
    "id_municipio",
    "ibge",
)
_DEFAULT_MUNICIPALITY_NAME_COLUMNS = (
    "municipio",
    "nome_municipio",
    "nm_municipio",
    "cidade",
    "localidade",
)


@dataclass(frozen=True)
class IndicatorSpec:
    code: str
    name: str
    unit: str
    category: str
    candidates: tuple[str, ...]
    aggregator: Literal["sum", "avg", "max", "min", "first"] = "sum"
    row_filters: dict[str, tuple[str, ...]] | None = None


@dataclass(frozen=True)
class TabularConnectorDefinition:
    job_name: str
    source: str
    dataset_name: str
    fact_dataset_name: str
    wave: str
    catalog_path: Path
    manual_dir: Path
    indicator_specs: tuple[IndicatorSpec, ...]
    dataset_version: str
    notes: str
    territory_scope: str = "municipality"
    municipality_code_columns: tuple[str, ...] = _DEFAULT_MUNICIPALITY_CODE_COLUMNS
    municipality_name_columns: tuple[str, ...] = _DEFAULT_MUNICIPALITY_NAME_COLUMNS
    reference_year_columns: tuple[str, ...] = ()
    prefer_manual_first: bool = False


def _normalize_text(value: str) -> str:
    stripped = value.strip().casefold()
    normalized = unicodedata.normalize("NFKD", stripped)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_column_name(value: str) -> str:
    base = _normalize_text(value)
    return re.sub(r"[^a-z0-9]+", "_", base).strip("_")


def _parse_reference_year(reference_period: str) -> str:
    token = str(reference_period).strip()
    if not token:
        raise ValueError("reference_period is empty")
    year = token.split("-")[0]
    if not year.isdigit() or len(year) != 4:
        raise ValueError(f"Invalid reference_period '{reference_period}'. Expected year (YYYY).")
    return year


def _parse_numeric(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and (math.isnan(value) or not math.isfinite(value)):
            return None
        return Decimal(str(value))

    token = str(value).strip()
    if not token or token in {"-", "...", "nan", "None"}:
        return None
    normalized = token.replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        parsed = Decimal(normalized)
        if parsed.is_nan():
            return None
        return parsed
    except InvalidOperation:
        return None


def _load_catalog(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    resources = payload.get("resources", [])
    if not isinstance(resources, list):
        raise ValueError(f"Invalid catalog format in {path}: 'resources' must be a list.")
    return [item for item in resources if isinstance(item, dict)]


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
    return str(row[0]).strip(), str(row[1]).strip(), str(row[2]).strip()


def _is_tabular_candidate(path_or_name: str) -> bool:
    suffix = Path(path_or_name).suffix.casefold()
    return suffix in {".csv", ".txt", ".xlsx", ".xls", ".zip", ".json"}


def _extract_tabular_bytes_from_zip(
    zip_bytes: bytes,
    *,
    preferred_names: tuple[str, ...] | None = None,
) -> tuple[bytes, str]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = [name for name in archive.namelist() if _is_tabular_candidate(name)]
        if not names:
            raise ValueError("ZIP file has no tabular entry.")
        selected: str | None = None
        normalized_preferences = tuple(
            _normalize_text(str(token))
            for token in (preferred_names or ())
            if str(token).strip()
        )
        if normalized_preferences:
            for candidate in sorted(names):
                normalized_candidate = _normalize_text(Path(candidate).stem)
                if any(token in normalized_candidate for token in normalized_preferences):
                    selected = candidate
                    break
        if selected is None:
            selected = sorted(names)[0]
        return archive.read(selected), Path(selected).suffix.casefold()


def _read_delimited_with_fallback(raw_bytes: bytes) -> pd.DataFrame:
    best_df: pd.DataFrame | None = None
    best_score: tuple[int, int] = (-1, -1)

    for encoding in ("utf-8", "latin1"):
        text = raw_bytes.decode(encoding, errors="replace")
        lines = text.splitlines()
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
        raise ValueError("Could not parse CSV/TXT with supported encodings/delimiters.")
    return best_df


def _read_json_payload(raw_bytes: bytes) -> pd.DataFrame:
    payload = json.loads(raw_bytes.decode("utf-8"))
    if isinstance(payload, list):
        return pd.DataFrame(payload)
    if not isinstance(payload, dict):
        raise ValueError("Unsupported JSON payload.")

    features = payload.get("features")
    if isinstance(features, list):
        rows: list[dict[str, Any]] = []
        for item in features:
            if not isinstance(item, dict):
                continue
            attrs = item.get("attributes")
            if isinstance(attrs, dict):
                rows.append(attrs)
            else:
                rows.append(item)
        if rows:
            return pd.DataFrame(rows)

    result = payload.get("result")
    if isinstance(result, dict):
        records = result.get("records")
        if isinstance(records, list):
            return pd.DataFrame(records)
    records = payload.get("records")
    if isinstance(records, list):
        return pd.DataFrame(records)
    return pd.DataFrame([payload])


def _load_dataframe_from_bytes(
    raw_bytes: bytes,
    *,
    suffix: str,
    preferred_zip_entry_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    normalized_suffix = suffix.casefold()
    if normalized_suffix == ".zip":
        inner_bytes, inner_suffix = _extract_tabular_bytes_from_zip(
            raw_bytes,
            preferred_names=preferred_zip_entry_names,
        )
        return _load_dataframe_from_bytes(inner_bytes, suffix=inner_suffix)
    if normalized_suffix in {".csv", ".txt"}:
        return _read_delimited_with_fallback(raw_bytes)
    if normalized_suffix in {".xlsx", ".xls"}:
        return pd.read_excel(io.BytesIO(raw_bytes))
    if normalized_suffix == ".json":
        return _read_json_payload(raw_bytes)
    raise ValueError(f"Unsupported dataset format '{suffix}'.")


def _list_manual_candidates(path: Path) -> list[Path]:
    if not path.exists():
        return []
    files = [p for p in path.iterdir() if p.is_file() and _is_tabular_candidate(p.name)]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def _normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={col: _normalize_column_name(str(col)) for col in df.columns})


def _to_digits(value: Any) -> str:
    text_value = str(value).strip()
    if text_value.endswith(".0"):
        text_value = text_value[:-2]
    return "".join(ch for ch in text_value if ch.isdigit())


def _resolve_municipality_rows(
    df: pd.DataFrame,
    *,
    municipality_ibge_code: str,
    municipality_name: str,
    code_columns: tuple[str, ...],
    name_columns: tuple[str, ...],
    source_file_name: str | None = None,
) -> list[dict[str, Any]]:
    if df.empty:
        return []
    normalized_df = _normalize_dataframe_columns(df)
    target_name = _normalize_text(municipality_name)
    code_candidates = {municipality_ibge_code}
    if len(municipality_ibge_code) >= 6:
        code_candidates.add(municipality_ibge_code[:6])

    matches: list[dict[str, Any]] = []
    seen_signatures: set[str] = set()

    has_code_columns = any(column in normalized_df.columns for column in code_columns)
    has_name_columns = any(column in normalized_df.columns for column in name_columns)

    for _, row in normalized_df.iterrows():
        row_dict = row.to_dict()
        signature = json.dumps({k: str(v) for k, v in row_dict.items()}, sort_keys=True, ensure_ascii=False)

        matched_by_code = False
        for column in code_columns:
            if column not in normalized_df.columns:
                continue
            if _to_digits(row.get(column)) in code_candidates:
                matched_by_code = True
                break

        matched_by_name = False
        if not matched_by_code:
            for column in name_columns:
                if column not in normalized_df.columns:
                    continue
                row_name = _normalize_text(str(row.get(column, "")))
                if row_name == target_name or target_name in row_name:
                    matched_by_name = True
                    break

        if matched_by_code or matched_by_name:
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                matches.append(row_dict)

    if (
        not matches
        and source_file_name
        and not has_code_columns
        and not has_name_columns
        and target_name
        and target_name in _normalize_text(Path(source_file_name).stem)
    ):
        return [row.to_dict() for _, row in normalized_df.iterrows()]

    return matches


def _extract_candidate_values(rows: list[dict[str, Any]], candidates: tuple[str, ...]) -> list[Decimal]:
    return _extract_candidate_values_with_filters(rows, candidates=candidates, row_filters=None)


def _row_matches_filters(
    row: dict[str, Any],
    *,
    row_filters: dict[str, tuple[str, ...]] | None,
) -> bool:
    if not row_filters:
        return True
    for raw_column, allowed_values in row_filters.items():
        column = _normalize_column_name(str(raw_column))
        if column not in row:
            return False
        row_value = _normalize_text(str(row.get(column, "")))
        allowed_tokens = tuple(_normalize_text(str(item)) for item in allowed_values if str(item).strip())
        if not allowed_tokens:
            continue
        if not any(token == row_value or token in row_value for token in allowed_tokens):
            return False
    return True


def _extract_candidate_values_with_filters(
    rows: list[dict[str, Any]],
    *,
    candidates: tuple[str, ...],
    row_filters: dict[str, tuple[str, ...]] | None,
) -> list[Decimal]:
    values: list[Decimal] = []
    for row in rows:
        if not _row_matches_filters(row, row_filters=row_filters):
            continue
        for key in candidates:
            if key not in row:
                continue
            value = _parse_numeric(row.get(key))
            if value is not None:
                values.append(value)
                break
    return values


def _aggregate_values(values: list[Decimal], aggregator: str) -> Decimal:
    if not values:
        raise ValueError("values must not be empty")
    if aggregator == "first":
        return values[0]
    if aggregator == "sum":
        return sum(values, Decimal("0"))
    if aggregator == "max":
        return max(values)
    if aggregator == "min":
        return min(values)
    if aggregator == "avg":
        return sum(values, Decimal("0")) / Decimal(str(len(values)))
    raise ValueError(f"Unsupported aggregator '{aggregator}'.")


def _value_matches_reference_year(value: Any, year: str) -> bool:
    token = str(value or "").strip()
    if not token:
        return False
    normalized = _to_digits(token)
    if len(normalized) >= 4 and normalized[:4] == year:
        return True
    return token.startswith(year)


def _filter_rows_by_reference_year(
    rows: list[dict[str, Any]],
    *,
    year: str,
    year_columns: tuple[str, ...],
) -> list[dict[str, Any]]:
    if not rows or not year_columns:
        return rows
    normalized_columns = tuple(_normalize_column_name(str(column)) for column in year_columns)
    filtered: list[dict[str, Any]] = []
    has_year_signal = False
    for row in rows:
        for column in normalized_columns:
            if column not in row:
                continue
            row_value = row.get(column)
            if str(row_value or "").strip():
                has_year_signal = True
            if _value_matches_reference_year(row.get(column), year):
                filtered.append(row)
                break
    if filtered:
        return filtered
    # If there is no usable year signal in the payload, keep backward-compatible fallback.
    if not has_year_signal:
        return rows
    # If year columns are present but no row matches the requested period, block the load.
    return []


def _build_indicator_rows(
    *,
    territory_id: str,
    reference_period: str,
    municipality_rows: list[dict[str, Any]],
    source: str,
    fact_dataset_name: str,
    indicator_specs: tuple[IndicatorSpec, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in indicator_specs:
        values = _extract_candidate_values_with_filters(
            municipality_rows,
            candidates=spec.candidates,
            row_filters=spec.row_filters,
        )
        if not values:
            continue
        value = _aggregate_values(values, spec.aggregator)
        rows.append(
            {
                "territory_id": territory_id,
                "source": source,
                "dataset": fact_dataset_name,
                "indicator_code": spec.code,
                "indicator_name": spec.name,
                "unit": spec.unit,
                "category": spec.category,
                "value": value,
                "reference_period": reference_period,
            }
        )
    return rows


def _render_uri_template(
    template: str,
    *,
    reference_period: str,
    municipality_ibge_code: str,
) -> str:
    municipality_ibge_code_6 = municipality_ibge_code[:6] if len(municipality_ibge_code) >= 6 else municipality_ibge_code
    return template.format(
        reference_period=reference_period,
        municipality_ibge_code=municipality_ibge_code,
        municipality_ibge_code_6=municipality_ibge_code_6,
    )


def _resolve_dataset(
    *,
    definition: TabularConnectorDefinition,
    reference_period: str,
    municipality_name: str,
    municipality_ibge_code: str,
    client: HttpClient,
) -> tuple[pd.DataFrame, bytes, str, str, str, str, list[str]] | None:
    warnings: list[str] = []
    resources = _load_catalog(definition.catalog_path)
    manual_candidates = _list_manual_candidates(definition.manual_dir)

    def _try_manual() -> tuple[pd.DataFrame, bytes, str, str, str, str, list[str]] | None:
        for candidate in manual_candidates:
            try:
                raw_bytes = candidate.read_bytes()
                suffix = candidate.suffix.casefold()
                df = _load_dataframe_from_bytes(raw_bytes, suffix=suffix)
                return df, raw_bytes, suffix, "manual", candidate.resolve().as_uri(), candidate.name, warnings
            except Exception as exc:
                warnings.append(f"{definition.source} manual source failed for '{candidate.name}': {exc}")
        return None

    def _try_remote() -> tuple[pd.DataFrame, bytes, str, str, str, str, list[str]] | None:
        for resource in resources:
            uri_template = str(resource.get("uri", "")).strip()
            if not uri_template:
                continue
            uri = _render_uri_template(
                uri_template,
                reference_period=reference_period,
                municipality_ibge_code=municipality_ibge_code,
            )
            suffix = (
                str(resource.get("extension", "")).strip().casefold()
                or Path(uri).suffix.casefold()
                or ".json"
            )
            try:
                raw_bytes, _content_type = client.download_bytes(uri, min_bytes=16)
                df = _load_dataframe_from_bytes(
                    raw_bytes,
                    suffix=suffix,
                    preferred_zip_entry_names=(
                        municipality_name,
                        municipality_ibge_code,
                        municipality_ibge_code[:6],
                    ),
                )
                return df, raw_bytes, suffix, "remote", uri, Path(uri).name, warnings
            except Exception as exc:
                warnings.append(f"{definition.source} remote source failed for '{uri}': {exc}")
        return None

    if definition.prefer_manual_first:
        manual_result = _try_manual()
        if manual_result is not None:
            return manual_result
        remote_result = _try_remote()
        if remote_result is not None:
            return remote_result
        return None

    remote_result = _try_remote()
    if remote_result is not None:
        return remote_result

    return _try_manual()


def _upsert_fact_indicator_rows(settings: Settings, load_rows: list[dict[str, Any]]) -> int:
    if not load_rows:
        return 0
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
                    "territory_id": row["territory_id"],
                    "source": row["source"],
                    "dataset": row["dataset"],
                    "indicator_code": row["indicator_code"],
                    "indicator_name": row["indicator_name"],
                    "unit": row["unit"],
                    "category": row["category"],
                    "value": str(row["value"]),
                    "reference_period": row["reference_period"],
                },
            )
    return len(load_rows)


def run_tabular_connector(
    definition: TabularConnectorDefinition,
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
    logger = get_logger(definition.job_name)
    run_id = str(uuid4())
    started_at_utc = datetime.now(UTC)
    started_at = time.perf_counter()
    warnings: list[str] = []
    check_prefix = _normalize_column_name(definition.source)

    try:
        parsed_reference_period = _parse_reference_year(reference_period)
        territory_id, municipality_name, municipality_ibge_code = _resolve_municipality_context(settings)
    except Exception as exc:
        return {
            "job": definition.job_name,
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
        dataset = _resolve_dataset(
            definition=definition,
            reference_period=parsed_reference_period,
            municipality_name=municipality_name,
            municipality_ibge_code=municipality_ibge_code,
            client=client,
        )
        if dataset is None:
            warnings.append(
                f"No {definition.source} source available (remote catalog and manual directory failed)."
            )
            elapsed = time.perf_counter() - started_at
            if not dry_run:
                with session_scope(settings) as session:
                    upsert_pipeline_run(
                        session=session,
                        run_id=run_id,
                        job_name=definition.job_name,
                        source=definition.source,
                        dataset=definition.dataset_name,
                        wave=definition.wave,
                        reference_period=parsed_reference_period,
                        started_at_utc=started_at_utc,
                        finished_at_utc=datetime.now(UTC),
                        status="blocked",
                        rows_extracted=0,
                        rows_loaded=0,
                        warnings_count=len(warnings),
                        errors_count=0,
                        details={"reason": "source_unavailable"},
                    )
                    replace_pipeline_checks_from_dicts(
                        session=session,
                        run_id=run_id,
                        checks=[
                            {
                                "name": f"{check_prefix}_source_resolved",
                                "status": "warn",
                                "details": warnings[-1],
                                "observed_value": 0,
                                "threshold_value": 1,
                            },
                            {
                                "name": f"{check_prefix}_indicator_rows_loaded",
                                "status": "warn",
                                "details": "0 indicator rows written because no source was available.",
                                "observed_value": 0,
                                "threshold_value": 1,
                            },
                        ],
                    )
            return {
                "job": definition.job_name,
                "status": "blocked",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": 0,
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
            }

        df, raw_bytes, source_suffix, source_type, source_uri, source_file_name, source_warnings = dataset
        warnings.extend(source_warnings)
        rows_extracted = len(df)

        municipality_rows = _resolve_municipality_rows(
            df,
            municipality_ibge_code=municipality_ibge_code,
            municipality_name=municipality_name,
            code_columns=definition.municipality_code_columns,
            name_columns=definition.municipality_name_columns,
            source_file_name=source_file_name,
        )
        municipality_rows = _filter_rows_by_reference_year(
            municipality_rows,
            year=parsed_reference_period,
            year_columns=definition.reference_year_columns,
        )
        if not municipality_rows:
            warnings.append(
                f"{definition.source} row not found for municipality code/name "
                f"({municipality_ibge_code}/{municipality_name})."
            )

        load_rows = _build_indicator_rows(
            territory_id=territory_id,
            reference_period=parsed_reference_period,
            municipality_rows=municipality_rows,
            source=definition.source,
            fact_dataset_name=definition.fact_dataset_name,
            indicator_specs=definition.indicator_specs,
        )

        if source_type == "remote" and not load_rows:
            for manual_candidate in _list_manual_candidates(definition.manual_dir):
                try:
                    manual_raw_bytes = manual_candidate.read_bytes()
                    manual_suffix = manual_candidate.suffix.casefold()
                    manual_df = _load_dataframe_from_bytes(manual_raw_bytes, suffix=manual_suffix)
                except Exception as exc:
                    warnings.append(
                        f"{definition.source} manual fallback failed for '{manual_candidate.name}': {exc}"
                    )
                    continue

                manual_rows = _resolve_municipality_rows(
                    manual_df,
                    municipality_ibge_code=municipality_ibge_code,
                    municipality_name=municipality_name,
                    code_columns=definition.municipality_code_columns,
                    name_columns=definition.municipality_name_columns,
                    source_file_name=manual_candidate.name,
                )
                manual_rows = _filter_rows_by_reference_year(
                    manual_rows,
                    year=parsed_reference_period,
                    year_columns=definition.reference_year_columns,
                )
                manual_load_rows = _build_indicator_rows(
                    territory_id=territory_id,
                    reference_period=parsed_reference_period,
                    municipality_rows=manual_rows,
                    source=definition.source,
                    fact_dataset_name=definition.fact_dataset_name,
                    indicator_specs=definition.indicator_specs,
                )
                if not manual_load_rows:
                    continue

                warnings.append(
                    f"{definition.source} remote payload produced no indicator rows; "
                    f"using manual fallback '{manual_candidate.name}'."
                )
                df = manual_df
                raw_bytes = manual_raw_bytes
                source_suffix = manual_suffix
                source_type = "manual"
                source_uri = manual_candidate.resolve().as_uri()
                source_file_name = manual_candidate.name
                rows_extracted = len(df)
                municipality_rows = manual_rows
                load_rows = manual_load_rows
                break

        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": definition.job_name,
                "status": "success" if load_rows else "blocked",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": rows_extracted,
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "preview": {
                    "source_type": source_type,
                    "source_uri": source_uri,
                    "source_file_name": source_file_name,
                    "municipality_matches": len(municipality_rows),
                    "indicators": [
                        {
                            "indicator_code": row["indicator_code"],
                            "value": str(row["value"]),
                        }
                        for row in load_rows
                    ],
                },
            }

        rows_written = _upsert_fact_indicator_rows(settings, load_rows)

        checks = [
            {
                "name": f"{check_prefix}_source_resolved",
                "status": "pass" if source_type in {"remote", "manual"} else "warn",
                "details": f"Source type resolved as {source_type}.",
                "observed_value": 1 if source_type in {"remote", "manual"} else 0,
                "threshold_value": 1,
            },
            {
                "name": f"{check_prefix}_municipality_row_found",
                "status": "pass" if municipality_rows else "warn",
                "details": (
                    f"Municipality should be present in {definition.source} dataset. "
                    f"Matches found: {len(municipality_rows)}."
                ),
                "observed_value": len(municipality_rows),
                "threshold_value": 1,
            },
            {
                "name": f"{check_prefix}_indicator_rows_loaded",
                "status": "pass" if rows_written > 0 else "warn",
                "details": f"{rows_written} indicator rows written.",
                "observed_value": rows_written,
                "threshold_value": 1,
            },
        ]

        bronze_payload = {
            "job": definition.job_name,
            "source": definition.source,
            "reference_period": parsed_reference_period,
            "source_type": source_type,
            "source_uri": source_uri,
            "source_file_name": source_file_name,
            "rows_extracted": rows_extracted,
            "rows_written": rows_written,
            "warnings": warnings,
            "municipality_matches": len(municipality_rows),
        }
        artifact = persist_raw_bytes(
            settings=settings,
            source=definition.source,
            dataset=definition.dataset_name,
            reference_period=parsed_reference_period,
            raw_bytes=raw_bytes
            if source_suffix in {".csv", ".txt", ".xlsx", ".xls", ".zip", ".json"}
            else json.dumps(bronze_payload, ensure_ascii=False).encode("utf-8"),
            extension=source_suffix if source_suffix else ".json",
            uri=source_uri,
            territory_scope=definition.territory_scope,
            dataset_version=definition.dataset_version,
            checks=checks,
            notes=definition.notes,
            run_id=run_id,
            tables_written=["silver.fact_indicator"] if rows_written > 0 else [],
            rows_written=(
                [{"table": "silver.fact_indicator", "rows": rows_written}] if rows_written > 0 else []
            ),
        )

        status = "success" if rows_written > 0 else "blocked"
        finished_at_utc = datetime.now(UTC)
        with session_scope(settings) as session:
            upsert_pipeline_run(
                session=session,
                run_id=run_id,
                job_name=definition.job_name,
                source=definition.source,
                dataset=definition.dataset_name,
                wave=definition.wave,
                reference_period=parsed_reference_period,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
                status=status,
                rows_extracted=rows_extracted,
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "source_type": source_type,
                    "source_file_name": source_file_name,
                    "rows_written": rows_written,
                    "municipality_matches": len(municipality_rows),
                },
            )
            replace_pipeline_checks_from_dicts(session=session, run_id=run_id, checks=checks)

        elapsed = time.perf_counter() - started_at
        logger.info(
            f"{definition.source} tabular job finished.",
            run_id=run_id,
            status=status,
            rows_extracted=rows_extracted,
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": definition.job_name,
            "status": status,
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": rows_extracted,
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
                        job_name=definition.job_name,
                        source=definition.source,
                        dataset=definition.dataset_name,
                        wave=definition.wave,
                        reference_period=parsed_reference_period,
                        started_at_utc=started_at_utc,
                        finished_at_utc=datetime.now(UTC),
                        status="failed",
                        rows_extracted=0,
                        rows_loaded=0,
                        warnings_count=len(warnings),
                        errors_count=1,
                        details={"error": str(exc)},
                    )
                    replace_pipeline_checks_from_dicts(
                        session=session,
                        run_id=run_id,
                        checks=[
                            {
                                "name": f"{check_prefix}_job_exception",
                                "status": "fail",
                                "details": (
                                    f"{definition.source} connector failed with exception: {exc}"
                                ),
                                "observed_value": 1,
                                "threshold_value": 0,
                            }
                        ],
                    )
            except Exception:
                logger.exception("Could not persist failed pipeline run in ops tables.", run_id=run_id)

        logger.exception(
            f"{definition.source} tabular job failed.",
            run_id=run_id,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": definition.job_name,
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
