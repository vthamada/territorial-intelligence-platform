from __future__ import annotations

import io
import json
import time
import unicodedata
import zipfile
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pandas as pd
from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run

JOB_NAME = "tse_electorate_fetch"
SOURCE = "TSE"
DATASET_NAME = "tse_perfil_eleitorado"
WAVE = "MVP-2"
PACKAGE_SHOW_PATH = "/package_show"

_ELECTORATE_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "ANO_ELEICAO": ("ANO_ELEICAO",),
    "NR_ZONA": ("NR_ZONA",),
    "SG_UF": ("SG_UF",),
    "NM_MUNICIPIO": ("NM_MUNICIPIO",),
    "DS_GENERO": ("DS_GENERO",),
    "DS_FAIXA_ETARIA": ("DS_FAIXA_ETARIA",),
    "DS_GRAU_ESCOLARIDADE": ("DS_GRAU_ESCOLARIDADE", "DS_GRAU_INSTRUCAO"),
    "QT_ELEITORES_PERFIL": ("QT_ELEITORES_PERFIL", "QT_ELEITORES"),
}
_SECTION_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "ANO_ELEICAO": ("ANO_ELEICAO", "AA_ELEICAO"),
    "NR_ZONA": ("NR_ZONA",),
    "NR_SECAO": ("NR_SECAO",),
    "NR_LOCAL_VOTACAO": ("NR_LOCAL_VOTACAO",),
    "NM_LOCAL_VOTACAO": ("NM_LOCAL_VOTACAO",),
    "SG_UF": ("SG_UF",),
    "NM_MUNICIPIO": ("NM_MUNICIPIO",),
    "DS_GENERO": ("DS_GENERO",),
    "DS_FAIXA_ETARIA": ("DS_FAIXA_ETARIA",),
    "DS_GRAU_ESCOLARIDADE": ("DS_GRAU_ESCOLARIDADE", "DS_GRAU_INSTRUCAO"),
    "QT_ELEITORES_PERFIL": ("QT_ELEITORES_PERFIL", "QT_ELEITORES"),
}
_LOCAL_VOTING_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "ANO_ELEICAO": ("AA_ELEICAO", "ANO_ELEICAO"),
    "NR_ZONA": ("NR_ZONA",),
    "NR_SECAO": ("NR_SECAO",),
    "NR_LOCAL_VOTACAO": ("NR_LOCAL_VOTACAO",),
    "NM_LOCAL_VOTACAO": ("NM_LOCAL_VOTACAO",),
    "SG_UF": ("SG_UF",),
    "NM_MUNICIPIO": ("NM_MUNICIPIO",),
    "QT_ELEITOR_SECAO": (
        "QT_ELEITOR_SECAO",
        "QT_ELEITOR_ELEICAO_FEDERAL",
        "QT_ELEITOR_ELEICAO_ESTADUAL",
        "QT_ELEITOR_ELEICAO_MUNICIPAL",
    ),
}
_MIN_REFERENCE_YEAR = 1900
_MAX_REFERENCE_YEAR_OFFSET = 1


def _normalize_text(value: str) -> str:
    stripped = value.strip().casefold()
    return "".join(ch for ch in unicodedata.normalize("NFKD", stripped) if not unicodedata.combining(ch))


def _safe_dimension(value: Any) -> str:
    raw = "" if value is None else str(value).strip()
    return raw if raw else "NAO_INFORMADO"


def _normalize_zone_code(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw.lower() == "nan":
        return None
    try:
        return str(int(float(raw)))
    except (TypeError, ValueError):
        return raw


def _normalize_section_code(value: Any) -> str | None:
    return _normalize_zone_code(value)


def _safe_optional_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    raw = str(value).strip()
    if not raw or raw.lower() == "nan":
        return None
    return raw


def _safe_optional_int(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _normalize_reference_year(value: Any, *, requested_year: int) -> tuple[int, bool]:
    max_allowed_year = datetime.now(UTC).year + _MAX_REFERENCE_YEAR_OFFSET
    try:
        raw_year = int(float(value))
    except (TypeError, ValueError):
        return requested_year, True
    if _MIN_REFERENCE_YEAR <= raw_year <= max_allowed_year:
        return raw_year, False
    return requested_year, True


def _resolve_municipality_context(settings: Settings) -> tuple[str, str, str]:
    with session_scope(settings) as session:
        row = session.execute(
            text(
                """
                SELECT territory_id::text, name, uf
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
    territory_id, name, uf = str(row[0]), str(row[1]).strip(), str(row[2]).strip().upper()
    if not territory_id:
        raise RuntimeError("Municipality territory_id is empty.")
    if not name:
        raise RuntimeError("Municipality name is empty in dim_territory.")
    if not uf:
        raise RuntimeError("Municipality UF is empty in dim_territory.")
    return territory_id, name, uf


def _ckan_get_package(client: HttpClient, base_url: str, package_id: str) -> dict[str, Any] | None:
    url = f"{base_url}{PACKAGE_SHOW_PATH}?id={package_id}"
    try:
        payload = client.get_json(url)
    except Exception:
        return None
    if not isinstance(payload, dict) or not payload.get("success"):
        return None
    result = payload.get("result")
    return result if isinstance(result, dict) else None


def _resolve_electorate_package(
    client: HttpClient,
    base_url: str,
    reference_year: int,
) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    warnings: list[str] = []
    candidate_ids = [
        f"eleitorado-{reference_year}",
        "eleitorado-2024",
        "eleitorado-2022",
        "eleitorado-2020",
        "eleitorado-2018",
        "eleitorado-2016",
        "eleitorado-atual",
    ]
    ordered_candidates = list(dict.fromkeys(candidate_ids))
    requested_id = f"eleitorado-{reference_year}"
    for package_id in ordered_candidates:
        package = _ckan_get_package(client, base_url, package_id)
        if package is None:
            continue
        if package_id != requested_id:
            warnings.append(
                f"CKAN package '{requested_id}' not found; fallback to '{package_id}'."
            )
        return package, package_id, warnings
    return None, None, warnings


def _pick_electorate_resource(resources: list[dict[str, Any]]) -> dict[str, Any] | None:
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        url = str(resource.get("url", "")).strip()
        name = str(resource.get("name", "")).strip().lower()
        if not url:
            continue
        if "perfil_eleitorado" in url and url.lower().endswith(".zip") and "local_votacao" not in url:
            return resource
        if "eleitorado -" in name and "local de votação" not in name and "deficiência" not in name:
            return resource
    return None


def _pick_electorate_section_resource(
    resources: list[dict[str, Any]],
    *,
    reference_year: int,
    uf: str,
) -> dict[str, Any] | None:
    expected_suffix = f"_{reference_year}_{uf.lower()}.zip"
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        url = str(resource.get("url", "")).strip().lower()
        name = str(resource.get("name", "")).strip().lower()
        if not url:
            continue
        if "perfil_eleitor_secao" in url and url.endswith(expected_suffix):
            return resource
        if "perfil do eleitorado por seção eleitoral" in name and f"{uf.lower()} -" in name:
            return resource
    return None


def _pick_local_voting_resource(
    resources: list[dict[str, Any]],
    *,
    reference_year: int,
) -> dict[str, Any] | None:
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        url = str(resource.get("url", "")).strip().lower()
        name = str(resource.get("name", "")).strip().lower()
        if not url:
            continue
        if "eleitorado_local_votacao" in url and f"_{reference_year}.zip" in url:
            return resource
        if "eleitorado por local de votação" in name and str(reference_year) in name:
            return resource
    return None


def _resolve_electorate_columns(columns: list[str]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for canonical, aliases in _ELECTORATE_COLUMN_ALIASES.items():
        if canonical == "NR_ZONA":
            selected_optional = next((alias for alias in aliases if alias in columns), None)
            if selected_optional is not None:
                resolved[canonical] = selected_optional
            continue
        selected = next((alias for alias in aliases if alias in columns), None)
        if selected is None:
            aliases_display = ", ".join(aliases)
            raise ValueError(
                f"Required electorate column '{canonical}' not found. "
                f"Accepted aliases: {aliases_display}."
            )
        resolved[canonical] = selected
    return resolved


def _resolve_required_columns(columns: list[str], aliases: dict[str, tuple[str, ...]]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for canonical, candidates in aliases.items():
        selected = next((candidate for candidate in candidates if candidate in columns), None)
        if selected is None:
            aliases_display = ", ".join(candidates)
            raise ValueError(
                f"Required electorate column '{canonical}' not found. "
                f"Accepted aliases: {aliases_display}."
            )
        resolved[canonical] = selected
    return resolved


def _extract_section_rows_from_zip(
    *,
    zip_bytes: bytes,
    municipality_name: str,
    uf: str,
    requested_year: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    target_name = _normalize_text(municipality_name)
    aggregated_sections: dict[tuple[int, str, str, str, str, str], int] = {}
    section_local_map: dict[tuple[int, str, str], tuple[str | None, str | None]] = {}
    csv_name = ""
    rows_scanned = 0
    rows_filtered = 0
    outlier_year_rows_rewritten = 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        csv_files = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_files:
            raise ValueError("Zip payload has no CSV file.")
        csv_name = csv_files[0]

        with archive.open(csv_name) as csv_bytes:
            wrapper = io.TextIOWrapper(csv_bytes, encoding="latin1", newline="")
            header_df = pd.read_csv(wrapper, sep=";", nrows=0, low_memory=False)
            column_mapping = _resolve_required_columns(list(header_df.columns), _SECTION_COLUMN_ALIASES)

        with archive.open(csv_name) as csv_bytes:
            wrapper = io.TextIOWrapper(csv_bytes, encoding="latin1", newline="")
            chunks = pd.read_csv(
                wrapper,
                sep=";",
                usecols=list(column_mapping.values()),
                chunksize=200_000,
                low_memory=False,
            )
            for chunk in chunks:
                chunk = chunk.rename(columns={actual: canonical for canonical, actual in column_mapping.items()})
                rows_scanned += len(chunk)
                filtered = chunk[
                    chunk["SG_UF"].astype(str).str.strip().str.upper().eq(uf)
                    & chunk["NM_MUNICIPIO"].astype(str).map(_normalize_text).eq(target_name)
                ]
                if filtered.empty:
                    continue

                filtered = filtered.copy()
                filtered["ANO_ELEICAO"] = pd.to_numeric(filtered["ANO_ELEICAO"], errors="coerce")
                filtered["QT_ELEITORES_PERFIL"] = pd.to_numeric(
                    filtered["QT_ELEITORES_PERFIL"],
                    errors="coerce",
                ).fillna(0)
                filtered["NR_ZONA"] = filtered["NR_ZONA"].map(_normalize_zone_code)
                filtered["NR_SECAO"] = filtered["NR_SECAO"].map(_normalize_section_code)
                filtered["NR_LOCAL_VOTACAO"] = filtered["NR_LOCAL_VOTACAO"].map(_normalize_zone_code)
                filtered["NM_LOCAL_VOTACAO"] = (
                    filtered["NM_LOCAL_VOTACAO"].astype(str).str.strip().replace({"": None, "nan": None})
                )

                filtered = filtered[
                    filtered["QT_ELEITORES_PERFIL"] >= 0
                    & filtered["NR_ZONA"].notna()
                    & filtered["NR_SECAO"].notna()
                ]
                filtered = filtered.dropna(subset=["ANO_ELEICAO"])
                if filtered.empty:
                    continue
                rows_filtered += len(filtered)

                for row in filtered[["ANO_ELEICAO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO"]].itertuples(index=False):
                    year, replaced = _normalize_reference_year(row.ANO_ELEICAO, requested_year=requested_year)
                    if replaced:
                        outlier_year_rows_rewritten += 1
                    section_local_map[(year, row.NR_ZONA, row.NR_SECAO)] = (row.NR_LOCAL_VOTACAO, row.NM_LOCAL_VOTACAO)

                grouped = (
                    filtered.groupby(
                        [
                            "ANO_ELEICAO",
                            "NR_ZONA",
                            "NR_SECAO",
                            "DS_GENERO",
                            "DS_FAIXA_ETARIA",
                            "DS_GRAU_ESCOLARIDADE",
                        ],
                        dropna=False,
                    )["QT_ELEITORES_PERFIL"]
                    .sum()
                    .reset_index()
                )
                for row in grouped.itertuples(index=False):
                    year, replaced = _normalize_reference_year(
                        row.ANO_ELEICAO,
                        requested_year=requested_year,
                    )
                    if replaced:
                        outlier_year_rows_rewritten += 1
                    key = (
                        year,
                        str(row.NR_ZONA),
                        str(row.NR_SECAO),
                        _safe_dimension(row.DS_GENERO),
                        _safe_dimension(row.DS_FAIXA_ETARIA),
                        _safe_dimension(row.DS_GRAU_ESCOLARIDADE),
                    )
                    aggregated_sections[key] = aggregated_sections.get(key, 0) + int(row.QT_ELEITORES_PERFIL)

    section_rows: list[dict[str, Any]] = []
    for (year, zone, section, sex, age, education), voters in sorted(aggregated_sections.items()):
        local_code, local_name = section_local_map.get((year, zone, section), (None, None))
        section_rows.append(
            {
                "reference_year": year,
                "tse_zone": zone,
                "tse_section": section,
                "nr_local_votacao": local_code,
                "local_votacao": local_name,
                "sex": sex,
                "age_range": age,
                "education": education,
                "voters": voters,
            }
        )

    info = {
        "csv_name": csv_name,
        "rows_scanned": rows_scanned,
        "rows_filtered": rows_filtered,
        "rows_aggregated_section": len(section_rows),
        "outlier_year_rows_rewritten": outlier_year_rows_rewritten,
    }
    return section_rows, info


def _extract_local_voting_metadata_from_zip(
    *,
    zip_bytes: bytes,
    municipality_name: str,
    uf: str,
    requested_year: int,
) -> tuple[dict[tuple[int, str, str], dict[str, Any]], dict[str, Any]]:
    target_name = _normalize_text(municipality_name)
    section_metadata: dict[tuple[int, str, str], dict[str, Any]] = {}
    csv_name = ""
    rows_scanned = 0
    rows_filtered = 0
    outlier_year_rows_rewritten = 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        csv_files = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_files:
            raise ValueError("Zip payload has no CSV file.")
        csv_name = csv_files[0]

        with archive.open(csv_name) as csv_bytes:
            wrapper = io.TextIOWrapper(csv_bytes, encoding="latin1", newline="")
            header_df = pd.read_csv(wrapper, sep=";", nrows=0, low_memory=False)
            column_mapping = _resolve_required_columns(list(header_df.columns), _LOCAL_VOTING_COLUMN_ALIASES)

        with archive.open(csv_name) as csv_bytes:
            wrapper = io.TextIOWrapper(csv_bytes, encoding="latin1", newline="")
            chunks = pd.read_csv(
                wrapper,
                sep=";",
                usecols=list(column_mapping.values()),
                chunksize=200_000,
                low_memory=False,
            )
            for chunk in chunks:
                chunk = chunk.rename(columns={actual: canonical for canonical, actual in column_mapping.items()})
                rows_scanned += len(chunk)
                filtered = chunk[
                    chunk["SG_UF"].astype(str).str.strip().str.upper().eq(uf)
                    & chunk["NM_MUNICIPIO"].astype(str).map(_normalize_text).eq(target_name)
                ]
                if filtered.empty:
                    continue
                filtered = filtered.copy()
                filtered["ANO_ELEICAO"] = pd.to_numeric(filtered["ANO_ELEICAO"], errors="coerce")
                filtered["QT_ELEITOR_SECAO"] = pd.to_numeric(filtered["QT_ELEITOR_SECAO"], errors="coerce").fillna(0)
                filtered["NR_ZONA"] = filtered["NR_ZONA"].map(_normalize_zone_code)
                filtered["NR_SECAO"] = filtered["NR_SECAO"].map(_normalize_section_code)
                filtered["NR_LOCAL_VOTACAO"] = filtered["NR_LOCAL_VOTACAO"].map(_normalize_zone_code)
                filtered["NM_LOCAL_VOTACAO"] = (
                    filtered["NM_LOCAL_VOTACAO"].astype(str).str.strip().replace({"": None, "nan": None})
                )

                filtered = filtered[
                    filtered["NR_ZONA"].notna()
                    & filtered["NR_SECAO"].notna()
                    & (filtered["QT_ELEITOR_SECAO"] >= 0)
                ]
                filtered = filtered.dropna(subset=["ANO_ELEICAO"])
                if filtered.empty:
                    continue
                rows_filtered += len(filtered)

                grouped = (
                    filtered.groupby(
                        ["ANO_ELEICAO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO"],
                        dropna=False,
                    )["QT_ELEITOR_SECAO"]
                    .max()
                    .reset_index()
                )
                for row in grouped.itertuples(index=False):
                    year, replaced = _normalize_reference_year(row.ANO_ELEICAO, requested_year=requested_year)
                    if replaced:
                        outlier_year_rows_rewritten += 1
                    key = (year, str(row.NR_ZONA), str(row.NR_SECAO))
                    section_metadata[key] = {
                        "nr_local_votacao": row.NR_LOCAL_VOTACAO,
                        "local_votacao": row.NM_LOCAL_VOTACAO,
                        "voters_section": int(row.QT_ELEITOR_SECAO),
                    }

    info = {
        "csv_name": csv_name,
        "rows_scanned": rows_scanned,
        "rows_filtered": rows_filtered,
        "rows_aggregated_section": len(section_metadata),
        "outlier_year_rows_rewritten": outlier_year_rows_rewritten,
    }
    return section_metadata, info


def _extract_rows_from_zip(
    *,
    zip_bytes: bytes,
    municipality_name: str,
    uf: str,
    requested_year: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    target_name = _normalize_text(municipality_name)
    aggregated_municipality: dict[tuple[int, str, str, str], int] = {}
    aggregated_zone: dict[tuple[int, str, str, str, str], int] = {}
    csv_name = ""
    rows_scanned = 0
    rows_filtered = 0
    outlier_year_rows_rewritten = 0
    column_mapping: dict[str, str] = {}

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        csv_files = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_files:
            raise ValueError("Zip payload has no CSV file.")
        csv_name = csv_files[0]

        with archive.open(csv_name) as csv_bytes:
            wrapper = io.TextIOWrapper(csv_bytes, encoding="latin1", newline="")
            header_df = pd.read_csv(wrapper, sep=";", nrows=0, low_memory=False)
            column_mapping = _resolve_electorate_columns(list(header_df.columns))

        with archive.open(csv_name) as csv_bytes:
            wrapper = io.TextIOWrapper(csv_bytes, encoding="latin1", newline="")
            chunks = pd.read_csv(
                wrapper,
                sep=";",
                usecols=list(column_mapping.values()),
                chunksize=200_000,
                low_memory=False,
            )
            for chunk in chunks:
                chunk = chunk.rename(columns={actual: canonical for canonical, actual in column_mapping.items()})
                rows_scanned += len(chunk)
                filtered = chunk[
                    chunk["SG_UF"].astype(str).str.strip().str.upper().eq(uf)
                    & chunk["NM_MUNICIPIO"].astype(str).map(_normalize_text).eq(target_name)
                ]
                if filtered.empty:
                    continue

                filtered = filtered.copy()
                filtered["ANO_ELEICAO"] = pd.to_numeric(filtered["ANO_ELEICAO"], errors="coerce")
                filtered["QT_ELEITORES_PERFIL"] = pd.to_numeric(
                    filtered["QT_ELEITORES_PERFIL"],
                    errors="coerce",
                ).fillna(0)
                filtered = filtered[filtered["QT_ELEITORES_PERFIL"] >= 0]
                filtered = filtered.dropna(subset=["ANO_ELEICAO"])
                if filtered.empty:
                    continue

                rows_filtered += len(filtered)
                grouped = (
                    filtered.groupby(
                    ["ANO_ELEICAO", "DS_GENERO", "DS_FAIXA_ETARIA", "DS_GRAU_ESCOLARIDADE"],
                    dropna=False,
                )["QT_ELEITORES_PERFIL"]
                    .sum()
                    .reset_index()
                )
                for row in grouped.itertuples(index=False):
                    year, replaced = _normalize_reference_year(
                        row.ANO_ELEICAO,
                        requested_year=requested_year,
                    )
                    if replaced:
                        outlier_year_rows_rewritten += 1
                    sex = _safe_dimension(row.DS_GENERO)
                    age = _safe_dimension(row.DS_FAIXA_ETARIA)
                    education = _safe_dimension(row.DS_GRAU_ESCOLARIDADE)
                    voters = int(row.QT_ELEITORES_PERFIL)
                    key = (year, sex, age, education)
                    aggregated_municipality[key] = aggregated_municipality.get(key, 0) + voters

                if "NR_ZONA" in filtered.columns:
                    filtered["NR_ZONA"] = filtered["NR_ZONA"].map(_normalize_zone_code)
                    grouped_zone = (
                        filtered[filtered["NR_ZONA"].notna()]
                        .groupby(
                            [
                                "ANO_ELEICAO",
                                "NR_ZONA",
                                "DS_GENERO",
                                "DS_FAIXA_ETARIA",
                                "DS_GRAU_ESCOLARIDADE",
                            ],
                            dropna=False,
                        )["QT_ELEITORES_PERFIL"]
                        .sum()
                        .reset_index()
                    )
                    for row in grouped_zone.itertuples(index=False):
                        zone_code = _normalize_zone_code(row.NR_ZONA)
                        if zone_code is None:
                            continue
                        year, replaced = _normalize_reference_year(
                            row.ANO_ELEICAO,
                            requested_year=requested_year,
                        )
                        if replaced:
                            outlier_year_rows_rewritten += 1
                        sex = _safe_dimension(row.DS_GENERO)
                        age = _safe_dimension(row.DS_FAIXA_ETARIA)
                        education = _safe_dimension(row.DS_GRAU_ESCOLARIDADE)
                        voters = int(row.QT_ELEITORES_PERFIL)
                        key_zone = (year, zone_code, sex, age, education)
                        aggregated_zone[key_zone] = aggregated_zone.get(key_zone, 0) + voters

    municipality_rows = [
        {
            "reference_year": year,
            "sex": sex,
            "age_range": age,
            "education": education,
            "voters": voters,
        }
        for (year, sex, age, education), voters in sorted(aggregated_municipality.items())
    ]
    zone_rows = [
        {
            "reference_year": year,
            "tse_zone": zone_code,
            "sex": sex,
            "age_range": age,
            "education": education,
            "voters": voters,
        }
        for (year, zone_code, sex, age, education), voters in sorted(aggregated_zone.items())
    ]

    info = {
        "csv_name": csv_name,
        "rows_scanned": rows_scanned,
        "rows_filtered": rows_filtered,
        "rows_aggregated_municipality": len(municipality_rows),
        "rows_aggregated_zone": len(zone_rows),
        "has_zone_column": "NR_ZONA" in column_mapping,
        "requested_year": requested_year,
        "column_mapping": column_mapping,
        "outlier_year_rows_rewritten": outlier_year_rows_rewritten,
    }
    return municipality_rows, zone_rows, info


def _upsert_electoral_zone(
    *,
    session: Any,
    municipality_territory_id: str,
    municipality_ibge_code: str,
    uf: str,
    zone_code: str,
) -> str:
    row = session.execute(
        text(
            """
            INSERT INTO silver.dim_territory (
                level,
                parent_territory_id,
                canonical_key,
                source_system,
                source_entity_id,
                ibge_geocode,
                tse_zone,
                tse_section,
                name,
                normalized_name,
                uf,
                municipality_ibge_code,
                geometry,
                metadata
            )
            VALUES (
                CAST('electoral_zone' AS silver.territory_level),
                CAST(:parent_territory_id AS uuid),
                :canonical_key,
                'TSE',
                :source_entity_id,
                :ibge_geocode,
                :tse_zone,
                '',
                :name,
                :normalized_name,
                :uf,
                :municipality_ibge_code,
                (
                    SELECT
                        CASE
                            WHEN geometry IS NULL THEN NULL
                            ELSE ST_PointOnSurface(geometry)
                        END
                    FROM silver.dim_territory
                    WHERE territory_id = CAST(:parent_territory_id AS uuid)
                    LIMIT 1
                ),
                CAST(:metadata AS jsonb)
            )
            ON CONFLICT (level, ibge_geocode, tse_zone, tse_section, municipality_ibge_code)
            DO UPDATE SET
                parent_territory_id = EXCLUDED.parent_territory_id,
                canonical_key = EXCLUDED.canonical_key,
                source_entity_id = EXCLUDED.source_entity_id,
                name = EXCLUDED.name,
                normalized_name = EXCLUDED.normalized_name,
                uf = EXCLUDED.uf,
                geometry = COALESCE(EXCLUDED.geometry, silver.dim_territory.geometry),
                metadata = COALESCE(silver.dim_territory.metadata, '{}'::jsonb) || EXCLUDED.metadata,
                updated_at = NOW()
            RETURNING territory_id::text
            """
        ),
        {
            "parent_territory_id": municipality_territory_id,
            "canonical_key": f"electoral_zone:tse:{municipality_ibge_code}:{zone_code}",
            "source_entity_id": f"{uf}-{municipality_ibge_code}-{zone_code}",
            "ibge_geocode": municipality_ibge_code,
            "tse_zone": zone_code,
            "name": f"Zona {zone_code}",
            "normalized_name": _normalize_text(f"Zona {zone_code}"),
            "uf": uf,
            "municipality_ibge_code": municipality_ibge_code,
            "metadata": json.dumps(
                {
                    "official_status": "proxy",
                    "proxy_method": "Zona agregada em ponto representativo da geometria municipal.",
                    "source": SOURCE,
                    "dataset": DATASET_NAME,
                }
            ),
        },
    ).first()
    if row is None:
        raise RuntimeError(f"Could not upsert electoral zone {zone_code}.")
    return str(row[0])


def _upsert_electoral_section(
    *,
    session: Any,
    zone_territory_id: str,
    municipality_name: str,
    municipality_ibge_code: str,
    uf: str,
    zone_code: str,
    section_code: str,
    polling_place_name: str | None = None,
    polling_place_code: str | None = None,
    voters_section: int | None = None,
) -> str:
    polling_place_name = _safe_optional_text(polling_place_name)
    polling_place_code = _safe_optional_text(polling_place_code)
    voters_section = _safe_optional_int(voters_section)

    section_name = f"Secao eleitoral {section_code} (zona {zone_code}) - {municipality_name}"
    metadata: dict[str, Any] = {
        "official_status": "proxy",
        "proxy_method": "Secao agregada em ponto representativo da geometria da zona eleitoral.",
        "source": SOURCE,
        "dataset": DATASET_NAME,
    }
    if polling_place_name:
        metadata["polling_place_name"] = polling_place_name
    if polling_place_code:
        metadata["polling_place_code"] = polling_place_code
    if voters_section is not None:
        metadata["voters_section"] = voters_section

    row = session.execute(
        text(
            """
            INSERT INTO silver.dim_territory (
                level,
                parent_territory_id,
                canonical_key,
                source_system,
                source_entity_id,
                ibge_geocode,
                tse_zone,
                tse_section,
                name,
                normalized_name,
                uf,
                municipality_ibge_code,
                geometry,
                metadata
            )
            VALUES (
                CAST('electoral_section' AS silver.territory_level),
                CAST(:parent_territory_id AS uuid),
                :canonical_key,
                'TSE',
                :source_entity_id,
                :ibge_geocode,
                :tse_zone,
                :tse_section,
                :name,
                :normalized_name,
                :uf,
                :municipality_ibge_code,
                (
                    SELECT
                        CASE
                            WHEN geometry IS NULL THEN NULL
                            ELSE ST_PointOnSurface(geometry)
                        END
                    FROM silver.dim_territory
                    WHERE territory_id = CAST(:parent_territory_id AS uuid)
                    LIMIT 1
                ),
                CAST(:metadata AS jsonb)
            )
            ON CONFLICT (level, ibge_geocode, tse_zone, tse_section, municipality_ibge_code)
            DO UPDATE SET
                parent_territory_id = EXCLUDED.parent_territory_id,
                canonical_key = EXCLUDED.canonical_key,
                source_entity_id = EXCLUDED.source_entity_id,
                name = EXCLUDED.name,
                normalized_name = EXCLUDED.normalized_name,
                uf = EXCLUDED.uf,
                geometry = COALESCE(EXCLUDED.geometry, silver.dim_territory.geometry),
                metadata = COALESCE(silver.dim_territory.metadata, '{}'::jsonb) || EXCLUDED.metadata,
                updated_at = NOW()
            RETURNING territory_id::text
            """
        ),
        {
            "parent_territory_id": zone_territory_id,
            "canonical_key": f"electoral_section:tse:{municipality_ibge_code}:{zone_code}:{section_code}",
            "source_entity_id": f"{uf}-{municipality_ibge_code}-{zone_code}-{section_code}",
            "ibge_geocode": municipality_ibge_code,
            "tse_zone": zone_code,
            "tse_section": section_code,
            "name": section_name,
            "normalized_name": _normalize_text(section_name),
            "uf": uf,
            "municipality_ibge_code": municipality_ibge_code,
            "metadata": json.dumps(metadata),
        },
    ).first()
    if row is None:
        raise RuntimeError(f"Could not upsert electoral section {section_code} (zone {zone_code}).")
    return str(row[0])


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

    client = HttpClient.from_settings(
        settings,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    try:
        reference_year = int(reference_period)
    except ValueError:
        return {
            "job": JOB_NAME,
            "status": "failed",
            "run_id": run_id,
            "duration_seconds": 0.0,
            "rows_extracted": 0,
            "rows_written": 0,
            "warnings": warnings,
            "errors": [f"Invalid reference_period '{reference_period}'. Expected year (YYYY)."],
        }

    try:
        territory_id, municipality_name, uf = _resolve_municipality_context(settings)

        package, effective_package_id, package_warnings = _resolve_electorate_package(
            client,
            settings.tse_ckan_base_url,
            reference_year,
        )
        warnings.extend(package_warnings)
        if package is None:
            raise RuntimeError("Could not resolve electorate package from TSE CKAN.")
        if effective_package_id is None:
            raise RuntimeError("Could not determine electorate package identifier.")

        resources = package.get("resources", [])
        if not isinstance(resources, list):
            raise RuntimeError("Invalid resources format in TSE CKAN package.")
        resource = _pick_electorate_resource(resources)
        if resource is None:
            raise RuntimeError("No electorate zip resource found in TSE CKAN package.")
        section_resource = _pick_electorate_section_resource(
            resources,
            reference_year=reference_year,
            uf=uf,
        )
        local_voting_resource = _pick_local_voting_resource(resources, reference_year=reference_year)

        resource_url = str(resource.get("url", "")).strip()
        if not resource_url:
            raise RuntimeError("Selected TSE resource has empty URL.")

        zip_bytes, _ = client.download_bytes(
            resource_url,
            expected_content_types=["zip", "octet-stream", "application/octet-stream"],
            min_bytes=1024,
        )

        parsed_rows_municipality, parsed_rows_zone, parse_info = _extract_rows_from_zip(
            zip_bytes=zip_bytes,
            municipality_name=municipality_name,
            uf=uf,
            requested_year=reference_year,
        )

        parsed_rows_section: list[dict[str, Any]] = []
        section_parse_info: dict[str, Any] | None = None
        section_resource_url: str | None = None
        if section_resource is not None:
            section_resource_url = str(section_resource.get("url", "")).strip()
            if section_resource_url:
                section_zip_bytes, _ = client.download_bytes(
                    section_resource_url,
                    expected_content_types=["zip", "octet-stream", "application/octet-stream"],
                    min_bytes=1024,
                )
                parsed_rows_section, section_parse_info = _extract_section_rows_from_zip(
                    zip_bytes=section_zip_bytes,
                    municipality_name=municipality_name,
                    uf=uf,
                    requested_year=reference_year,
                )
        else:
            warnings.append(
                f"No section-level electorate resource found for UF={uf} and year={reference_year}."
            )

        local_voting_info: dict[str, Any] | None = None
        local_voting_resource_url: str | None = None
        local_voting_section_metadata: dict[tuple[int, str, str], dict[str, Any]] = {}
        if local_voting_resource is not None:
            local_voting_resource_url = str(local_voting_resource.get("url", "")).strip()
            if local_voting_resource_url:
                local_voting_zip_bytes, _ = client.download_bytes(
                    local_voting_resource_url,
                    expected_content_types=["zip", "octet-stream", "application/octet-stream"],
                    min_bytes=1024,
                )
                local_voting_section_metadata, local_voting_info = _extract_local_voting_metadata_from_zip(
                    zip_bytes=local_voting_zip_bytes,
                    municipality_name=municipality_name,
                    uf=uf,
                    requested_year=reference_year,
                )

        if parsed_rows_section and local_voting_section_metadata:
            for row in parsed_rows_section:
                section_key = (row["reference_year"], row["tse_zone"], row["tse_section"])
                local_meta = local_voting_section_metadata.get(section_key)
                if local_meta is None:
                    continue
                if not row.get("nr_local_votacao"):
                    row["nr_local_votacao"] = local_meta.get("nr_local_votacao")
                if not row.get("local_votacao"):
                    row["local_votacao"] = local_meta.get("local_votacao")
                row["voters_section"] = local_meta.get("voters_section")

        extracted_years = sorted(
            {
                int(item["reference_year"])
                for item in (*parsed_rows_municipality, *parsed_rows_zone, *parsed_rows_section)
                if item.get("reference_year") is not None
            }
        )
        if extracted_years and reference_year not in extracted_years:
            warnings.append(
                (
                    f"Requested reference_year={reference_year}, but extracted election years are "
                    f"{', '.join(str(year) for year in extracted_years)}."
                )
            )
        if not parsed_rows_municipality and not parsed_rows_zone and not parsed_rows_section:
            warnings.append(
                f"No electorate rows found for municipality '{municipality_name}' ({uf})."
            )
        if not parse_info.get("has_zone_column", False):
            warnings.append(
                "Electorate dataset has no zone column (NR_ZONA); zone-level electorate rows were not generated."
            )

        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": JOB_NAME,
                "status": "success",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": len(parsed_rows_municipality) + len(parsed_rows_zone) + len(parsed_rows_section),
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "preview": {
                    "package_id": effective_package_id,
                    "resource_url": resource_url,
                    "parse_info": parse_info,
                    "section_resource_url": section_resource_url,
                    "section_parse_info": section_parse_info,
                    "local_voting_resource_url": local_voting_resource_url,
                    "local_voting_info": local_voting_info,
                },
            }

        rows_written = 0
        municipality_rows_written = 0
        zone_rows_written = 0
        section_rows_written = 0
        if parsed_rows_municipality or parsed_rows_zone or parsed_rows_section:
            with session_scope(settings) as session:
                zone_territory_ids: dict[str, str] = {}
                zone_codes = {
                    str(item["tse_zone"]) for item in parsed_rows_zone
                } | {
                    str(item["tse_zone"]) for item in parsed_rows_section
                }
                for zone_code in sorted(zone_codes):
                    zone_territory_ids[zone_code] = _upsert_electoral_zone(
                        session=session,
                        municipality_territory_id=territory_id,
                        municipality_ibge_code=settings.municipality_ibge_code,
                        uf=uf,
                        zone_code=zone_code,
                    )

                for row in parsed_rows_municipality:
                    session.execute(
                        text(
                            """
                            INSERT INTO silver.fact_electorate (
                                territory_id,
                                reference_year,
                                sex,
                                age_range,
                                education,
                                voters
                            )
                            VALUES (
                                CAST(:territory_id AS uuid),
                                :reference_year,
                                :sex,
                                :age_range,
                                :education,
                                :voters
                            )
                            ON CONFLICT (
                                territory_id,
                                reference_year,
                                sex,
                                age_range,
                                education
                            )
                            DO UPDATE SET
                                voters = EXCLUDED.voters
                            """
                        ),
                        {
                            "territory_id": territory_id,
                            "reference_year": row["reference_year"],
                            "sex": row["sex"],
                            "age_range": row["age_range"],
                            "education": row["education"],
                            "voters": row["voters"],
                        },
                    )
                    rows_written += 1
                    municipality_rows_written += 1

                for row in parsed_rows_zone:
                    zone_id = zone_territory_ids.get(str(row["tse_zone"]))
                    if zone_id is None:
                        warnings.append(
                            f"Skipped electorate row because zone territory could not be resolved: {row['tse_zone']}."
                        )
                        continue
                    session.execute(
                        text(
                            """
                            INSERT INTO silver.fact_electorate (
                                territory_id,
                                reference_year,
                                sex,
                                age_range,
                                education,
                                voters
                            )
                            VALUES (
                                CAST(:territory_id AS uuid),
                                :reference_year,
                                :sex,
                                :age_range,
                                :education,
                                :voters
                            )
                            ON CONFLICT (
                                territory_id,
                                reference_year,
                                sex,
                                age_range,
                                education
                            )
                            DO UPDATE SET
                                voters = EXCLUDED.voters
                            """
                        ),
                        {
                            "territory_id": zone_id,
                            "reference_year": row["reference_year"],
                            "sex": row["sex"],
                            "age_range": row["age_range"],
                            "education": row["education"],
                            "voters": row["voters"],
                        },
                    )
                    rows_written += 1
                    zone_rows_written += 1

                section_territory_ids: dict[tuple[str, str], str] = {}
                for section_row in parsed_rows_section:
                    section_key = (str(section_row["tse_zone"]), str(section_row["tse_section"]))
                    section_territory_id = section_territory_ids.get(section_key)
                    if section_territory_id is None:
                        zone_id = zone_territory_ids.get(section_key[0])
                        if zone_id is None:
                            warnings.append(
                                "Skipped electorate section row because zone territory could not be resolved: "
                                f"zone={section_key[0]} section={section_key[1]}."
                            )
                            continue
                        section_territory_id = _upsert_electoral_section(
                            session=session,
                            zone_territory_id=zone_id,
                            municipality_name=municipality_name,
                            municipality_ibge_code=settings.municipality_ibge_code,
                            uf=uf,
                            zone_code=section_key[0],
                            section_code=section_key[1],
                            polling_place_name=section_row.get("local_votacao"),
                            polling_place_code=section_row.get("nr_local_votacao"),
                            voters_section=section_row.get("voters_section"),
                        )
                        section_territory_ids[section_key] = section_territory_id

                    session.execute(
                        text(
                            """
                            INSERT INTO silver.fact_electorate (
                                territory_id,
                                reference_year,
                                sex,
                                age_range,
                                education,
                                voters
                            )
                            VALUES (
                                CAST(:territory_id AS uuid),
                                :reference_year,
                                :sex,
                                :age_range,
                                :education,
                                :voters
                            )
                            ON CONFLICT (
                                territory_id,
                                reference_year,
                                sex,
                                age_range,
                                education
                            )
                            DO UPDATE SET
                                voters = EXCLUDED.voters
                            """
                        ),
                        {
                            "territory_id": section_territory_id,
                            "reference_year": section_row["reference_year"],
                            "sex": section_row["sex"],
                            "age_range": section_row["age_range"],
                            "education": section_row["education"],
                            "voters": section_row["voters"],
                        },
                    )
                    rows_written += 1
                    section_rows_written += 1

        checks = [
            {
                "name": "ckan_package_resolved",
                "status": "pass",
                "details": f"Package '{effective_package_id}' resolved.",
            },
            {
                "name": "electorate_rows_extracted",
                "status": "pass" if parsed_rows_municipality or parsed_rows_zone or parsed_rows_section else "warn",
                "details": (
                    f"{len(parsed_rows_municipality)} municipality rows and "
                    f"{len(parsed_rows_zone)} zone rows and "
                    f"{len(parsed_rows_section)} section rows parsed."
                ),
            },
            {
                "name": "electorate_rows_loaded",
                "status": "pass" if rows_written > 0 else "warn",
                "details": f"{rows_written} rows upserted into silver.fact_electorate.",
            },
            {
                "name": "electorate_zone_rows_loaded",
                "status": "pass" if zone_rows_written > 0 else "warn",
                "details": f"{zone_rows_written} zone rows upserted into silver.fact_electorate.",
            },
            {
                "name": "electorate_section_rows_loaded",
                "status": "pass" if section_rows_written > 0 else "warn",
                "details": f"{section_rows_written} section rows upserted into silver.fact_electorate.",
            },
        ]
        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=reference_period,
            raw_bytes=zip_bytes,
            extension=".zip",
            uri=resource_url,
            territory_scope="municipality",
            dataset_version=effective_package_id,
            checks=checks,
            notes="TSE electorate extraction and Silver upsert for municipality scope.",
            run_id=run_id,
            tables_written=["silver.fact_electorate", "silver.dim_territory"],
            rows_written=[{"table": "silver.fact_electorate", "rows": rows_written}],
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
                reference_period=reference_period,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
                status="success",
                rows_extracted=len(parsed_rows_municipality) + len(parsed_rows_zone),
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "package_id": effective_package_id,
                    "resource_url": resource_url,
                    "parse_info": parse_info,
                    "section_resource_url": section_resource_url,
                    "section_parse_info": section_parse_info,
                    "local_voting_resource_url": local_voting_resource_url,
                    "local_voting_info": local_voting_info,
                    "municipality_rows_written": municipality_rows_written,
                    "zone_rows_written": zone_rows_written,
                    "section_rows_written": section_rows_written,
                },
            )
            replace_pipeline_checks_from_dicts(
                session=session,
                run_id=run_id,
                checks=[
                    {
                        "name": check["name"],
                        "status": check["status"],
                        "details": check["details"],
                    }
                    for check in checks
                ],
            )

        elapsed = time.perf_counter() - started_at
        logger.info(
            "TSE electorate job finished.",
            run_id=run_id,
            rows_extracted=len(parsed_rows_municipality) + len(parsed_rows_zone) + len(parsed_rows_section),
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "success",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": len(parsed_rows_municipality) + len(parsed_rows_zone) + len(parsed_rows_section),
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
                        reference_period=reference_period,
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
                logger.exception("Could not persist failed pipeline run in ops tables.", run_id=run_id)

        logger.exception(
            "TSE electorate job failed.",
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
