from __future__ import annotations

import io
import json
import re
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
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

JOB_NAME = "urban_transport_fetch"
SOURCE = "OSM"
DATASET_NAME = "urban_transport_catalog"
WAVE = "MVP-7"
CATALOG_PATH = Path("configs/urban_transport_catalog.yml")
MANUAL_DIRS = (Path("data/manual/urban/transport"), Path("data/manual/urban"))

_BUS_VALUES = {"bus_stop", "bus_station", "stop_position", "platform"}
_RAIL_VALUES = {"station", "halt", "tram_stop", "subway_entrance"}


def _normalize_column_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().casefold()).strip("_")


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    token = str(value).strip()
    if not token or token.casefold() in {"nan", "none", "null"}:
        return None
    return token


def _to_bool(value: Any) -> bool | None:
    token = str(value or "").strip().casefold()
    if not token:
        return None
    if token in {"yes", "true", "1", "sim"}:
        return True
    if token in {"no", "false", "0", "-1", "nao"}:
        return False
    return None


def _parse_reference_year(reference_period: str) -> str:
    token = str(reference_period).strip()
    if not token:
        raise ValueError("reference_period is empty")
    year = token.split("-")[0]
    if not year.isdigit() or len(year) != 4:
        raise ValueError(f"Invalid reference_period '{reference_period}'. Expected year (YYYY).")
    return year


def _load_catalog(path: Path = CATALOG_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    resources = payload.get("resources", [])
    if not isinstance(resources, list):
        raise ValueError("Invalid urban transport catalog format: 'resources' must be a list.")
    return [item for item in resources if isinstance(item, dict)]


def _resolve_municipality_context(settings: Settings) -> tuple[str, str, tuple[float, float, float, float]]:
    with session_scope(settings) as session:
        row = session.execute(
            text(
                """
                SELECT
                    territory_id::text,
                    name,
                    ST_XMin(ST_Envelope(geometry::geometry))::double precision AS minx,
                    ST_YMin(ST_Envelope(geometry::geometry))::double precision AS miny,
                    ST_XMax(ST_Envelope(geometry::geometry))::double precision AS maxx,
                    ST_YMax(ST_Envelope(geometry::geometry))::double precision AS maxy
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
    bbox = (float(row[2]), float(row[3]), float(row[4]), float(row[5]))
    return str(row[0]), str(row[1]).strip(), bbox


def _list_manual_candidates() -> list[Path]:
    candidates: list[Path] = []
    for directory in MANUAL_DIRS:
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if not path.is_file():
                continue
            if path.suffix.casefold() not in {".json", ".geojson", ".csv", ".txt", ".zip"}:
                continue
            candidates.append(path)
    return sorted(
        candidates,
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def _extract_from_zip(raw_bytes: bytes) -> tuple[bytes, str]:
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
        names = [
            name
            for name in archive.namelist()
            if Path(name).suffix.casefold() in {".json", ".geojson", ".csv", ".txt"}
        ]
        if not names:
            raise ValueError("ZIP file has no supported urban transport payload.")
        selected = sorted(names)[0]
        return archive.read(selected), Path(selected).suffix.casefold()


def _parse_tabular_bytes(raw_bytes: bytes) -> pd.DataFrame:
    for encoding in ("utf-8", "latin1"):
        for sep in (";", ",", "\t", "|"):
            try:
                return pd.read_csv(io.BytesIO(raw_bytes), encoding=encoding, sep=sep, low_memory=False)
            except Exception:
                continue
    raise ValueError("Could not parse CSV/TXT with supported encodings and delimiters.")


def _parse_payload_bytes(raw_bytes: bytes, *, suffix: str) -> tuple[Any, bytes, str]:
    normalized_suffix = suffix.casefold()
    if normalized_suffix == ".zip":
        inner_bytes, inner_suffix = _extract_from_zip(raw_bytes)
        return _parse_payload_bytes(inner_bytes, suffix=inner_suffix)
    if normalized_suffix in {".json", ".geojson"}:
        payload = json.loads(raw_bytes.decode("utf-8"))
        return payload, raw_bytes, normalized_suffix
    if normalized_suffix in {".csv", ".txt"}:
        dataframe = _parse_tabular_bytes(raw_bytes)
        return {"rows": dataframe.to_dict(orient="records")}, raw_bytes, normalized_suffix
    raise ValueError(f"Unsupported suffix for urban transport payload: {suffix}")


def _extract_point_geometry(element: dict[str, Any]) -> dict[str, Any] | None:
    element_type = str(element.get("type") or "").strip()
    if element_type == "node":
        lon = element.get("lon")
        lat = element.get("lat")
        if lon is None or lat is None:
            return None
        return {"type": "Point", "coordinates": [float(lon), float(lat)]}

    center = element.get("center")
    if isinstance(center, dict):
        lon = center.get("lon")
        lat = center.get("lat")
        if lon is not None and lat is not None:
            return {"type": "Point", "coordinates": [float(lon), float(lat)]}

    geometry = element.get("geometry")
    if isinstance(geometry, list) and geometry:
        first = geometry[0]
        if isinstance(first, dict):
            lon = first.get("lon")
            lat = first.get("lat")
            if lon is not None and lat is not None:
                return {"type": "Point", "coordinates": [float(lon), float(lat)]}
    return None


def _ensure_point_geometry(geometry: Any) -> dict[str, Any] | None:
    if not isinstance(geometry, dict):
        return None
    geometry_type = str(geometry.get("type", "")).strip()
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point" and isinstance(coordinates, list) and len(coordinates) == 2:
        return {"type": "Point", "coordinates": [float(coordinates[0]), float(coordinates[1])]}
    if geometry_type in {"LineString", "MultiPoint"} and isinstance(coordinates, list) and coordinates:
        first = coordinates[0]
        if isinstance(first, list) and len(first) >= 2:
            return {"type": "Point", "coordinates": [float(first[0]), float(first[1])]}
    if geometry_type == "Polygon" and isinstance(coordinates, list) and coordinates:
        ring = coordinates[0]
        if isinstance(ring, list) and ring:
            first = ring[0]
            if isinstance(first, list) and len(first) >= 2:
                return {"type": "Point", "coordinates": [float(first[0]), float(first[1])]}
    return None


def _resolve_mode(tags: dict[str, Any]) -> tuple[str, str | None]:
    amenity = str(tags.get("amenity") or "").strip().casefold()
    highway = str(tags.get("highway") or "").strip().casefold()
    railway = str(tags.get("railway") or "").strip().casefold()
    public_transport = str(tags.get("public_transport") or "").strip().casefold()

    if railway in _RAIL_VALUES:
        return "rail", railway
    if amenity == "ferry_terminal":
        return "ferry", "ferry_terminal"
    if highway in _BUS_VALUES or public_transport in _BUS_VALUES or amenity == "bus_station":
        return "bus", highway or public_transport or amenity
    if amenity == "taxi":
        return "road", "taxi"
    if public_transport:
        return "multimodal", public_transport
    if railway:
        return "rail", railway
    return "other", amenity or highway or railway or None


def _parse_overpass_rows(payload: dict[str, Any], *, reference_period: str) -> list[dict[str, Any]]:
    elements = payload.get("elements")
    if not isinstance(elements, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in elements:
        if not isinstance(item, dict):
            continue
        geometry = _extract_point_geometry(item)
        if geometry is None:
            continue
        tags = item.get("tags") if isinstance(item.get("tags"), dict) else {}
        mode, mode_detail = _resolve_mode(tags)
        rows.append(
            {
                "source": "OSM_OVERPASS",
                "external_id": f"{item.get('type')}/{item.get('id')}",
                "name": str(tags.get("name") or "").strip() or None,
                "mode": mode,
                "operator": _optional_text(tags.get("operator") or tags.get("network")),
                "is_accessible": _to_bool(tags.get("wheelchair")),
                "metadata_json": {
                    "reference_period": reference_period,
                    "mode_detail": mode_detail,
                    "raw_tags": tags,
                    "osm_type": str(item.get("type") or ""),
                },
                "geometry_json": json.dumps(geometry, ensure_ascii=False),
                "geometry_wkt": None,
            }
        )
    return rows


def _parse_geojson_rows(payload: dict[str, Any], *, reference_period: str) -> list[dict[str, Any]]:
    features = payload.get("features")
    if not isinstance(features, list):
        return []
    rows: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        geometry = _ensure_point_geometry(feature.get("geometry"))
        if geometry is None:
            continue
        properties = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
        mode, mode_detail = _resolve_mode(properties)
        rows.append(
            {
                "source": str(properties.get("source") or "MANUAL_URBAN").strip() or "MANUAL_URBAN",
                "external_id": str(
                    properties.get("external_id")
                    or properties.get("id")
                    or properties.get("osm_id")
                    or ""
                ).strip()
                or None,
                "name": str(properties.get("name") or "").strip() or None,
                "mode": str(properties.get("mode") or mode or "").strip() or "other",
                "operator": _optional_text(properties.get("operator") or properties.get("network")),
                "is_accessible": _to_bool(properties.get("is_accessible") or properties.get("wheelchair")),
                "metadata_json": {
                    "reference_period": reference_period,
                    "mode_detail": str(properties.get("mode_detail") or mode_detail or "").strip() or None,
                    "raw_properties": properties,
                    "feature_type": "geojson",
                },
                "geometry_json": json.dumps(geometry, ensure_ascii=False),
                "geometry_wkt": None,
            }
        )
    return rows


def _parse_tabular_rows(payload: dict[str, Any], *, reference_period: str) -> list[dict[str, Any]]:
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in raw_rows:
        if not isinstance(item, dict):
            continue
        normalized = {_normalize_column_name(key): value for key, value in item.items()}
        geometry_json_raw = normalized.get("geometry_json") or normalized.get("geom_json")
        geometry_wkt = normalized.get("geometry_wkt") or normalized.get("wkt")
        geometry_json: str | None = None

        if geometry_json_raw:
            try:
                geometry_payload = (
                    geometry_json_raw
                    if isinstance(geometry_json_raw, dict)
                    else json.loads(str(geometry_json_raw))
                )
                normalized_geometry = _ensure_point_geometry(geometry_payload)
                if normalized_geometry is not None:
                    geometry_json = json.dumps(normalized_geometry, ensure_ascii=False)
            except Exception:
                geometry_json = None

        if geometry_json is None and geometry_wkt is None:
            lon = normalized.get("lon") or normalized.get("longitude")
            lat = normalized.get("lat") or normalized.get("latitude")
            if lon is not None and lat is not None:
                geometry_json = json.dumps(
                    {"type": "Point", "coordinates": [float(lon), float(lat)]},
                    ensure_ascii=False,
                )
        if geometry_json is None and geometry_wkt is None:
            continue

        properties = {key: str(value) for key, value in normalized.items()}
        mode, mode_detail = _resolve_mode(normalized)
        rows.append(
            {
                "source": str(normalized.get("source") or "MANUAL_URBAN").strip() or "MANUAL_URBAN",
                "external_id": _optional_text(normalized.get("external_id") or normalized.get("id")),
                "name": _optional_text(normalized.get("name")),
                "mode": str(normalized.get("mode") or mode or "").strip() or "other",
                "operator": _optional_text(normalized.get("operator") or normalized.get("network")),
                "is_accessible": _to_bool(normalized.get("is_accessible") or normalized.get("wheelchair")),
                "metadata_json": {
                    "reference_period": reference_period,
                    "mode_detail": str(normalized.get("mode_detail") or mode_detail or "").strip() or None,
                    "raw_row": properties,
                    "feature_type": "tabular",
                },
                "geometry_json": geometry_json,
                "geometry_wkt": _optional_text(geometry_wkt),
            }
        )
    return rows


def _parse_transport_rows(payload: Any, *, reference_period: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("elements"), list):
        return _parse_overpass_rows(payload, reference_period=reference_period)
    if isinstance(payload.get("features"), list):
        return _parse_geojson_rows(payload, reference_period=reference_period)
    if isinstance(payload.get("rows"), list):
        return _parse_tabular_rows(payload, reference_period=reference_period)
    return []


def _resolve_dataset(
    *,
    reference_period: str,
    bbox: tuple[float, float, float, float],
    client: HttpClient,
) -> tuple[list[dict[str, Any]], bytes, str, str, str, str, list[str]] | None:
    warnings: list[str] = []
    minx, miny, maxx, maxy = bbox

    for resource in _load_catalog():
        uri_template = str(resource.get("uri", "")).strip()
        if not uri_template:
            continue
        uri = uri_template.format(
            reference_period=reference_period,
            minx=minx,
            miny=miny,
            maxx=maxx,
            maxy=maxy,
        )
        method = str(resource.get("method", "GET")).strip().upper() or "GET"
        suffix = str(resource.get("extension", ".json")).strip().casefold() or ".json"
        body_template = str(resource.get("body_template", "")).strip()
        try:
            if method == "POST":
                body = body_template.format(
                    reference_period=reference_period,
                    minx=minx,
                    miny=miny,
                    maxx=maxx,
                    maxy=maxy,
                )
                response = client._request("POST", uri, data={"data": body})  # noqa: SLF001
                raw_bytes = response.content
            else:
                raw_bytes, _content_type = client.download_bytes(uri, min_bytes=32)
            payload, raw_for_bronze, normalized_suffix = _parse_payload_bytes(raw_bytes, suffix=suffix)
            rows = _parse_transport_rows(payload, reference_period=reference_period)
            if rows:
                return rows, raw_for_bronze, normalized_suffix, "remote", uri, Path(uri).name, warnings
            warnings.append(f"Urban transport remote resource returned zero rows: {uri}")
        except Exception as exc:
            warnings.append(f"Urban transport remote source failed for '{uri}': {exc}")

    for candidate in _list_manual_candidates():
        try:
            raw_bytes = candidate.read_bytes()
            payload, raw_for_bronze, normalized_suffix = _parse_payload_bytes(
                raw_bytes,
                suffix=candidate.suffix.casefold(),
            )
            rows = _parse_transport_rows(payload, reference_period=reference_period)
            if rows:
                return (
                    rows,
                    raw_for_bronze,
                    normalized_suffix,
                    "manual",
                    candidate.resolve().as_uri(),
                    candidate.name,
                    warnings,
                )
            warnings.append(f"Urban transport manual source returned zero rows: {candidate.name}")
        except Exception as exc:
            warnings.append(f"Urban transport manual source failed for '{candidate.name}': {exc}")
    return None


def _replace_transport_rows(settings: Settings, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    unique_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        fingerprint = json.dumps(
            {
                "source": row.get("source"),
                "external_id": row.get("external_id"),
                "name": row.get("name"),
                "mode": row.get("mode"),
                "operator": row.get("operator"),
                "is_accessible": row.get("is_accessible"),
                "geometry_json": row.get("geometry_json"),
                "geometry_wkt": row.get("geometry_wkt"),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique_rows.append(row)

    sources = sorted({str(row.get("source") or "MANUAL_URBAN") for row in unique_rows})
    with session_scope(settings) as session:
        for source in sources:
            session.execute(
                text("DELETE FROM map.urban_transport_stop WHERE source = :source"),
                {"source": source},
            )
        for row in unique_rows:
            session.execute(
                text(
                    """
                    INSERT INTO map.urban_transport_stop (
                        source,
                        external_id,
                        name,
                        mode,
                        operator,
                        is_accessible,
                        metadata_json,
                        geom
                    )
                    VALUES (
                        :source,
                        :external_id,
                        :name,
                        :mode,
                        :operator,
                        :is_accessible,
                        CAST(:metadata_json AS jsonb),
                        ST_SetSRID(
                            CASE
                                WHEN CAST(:geometry_json AS TEXT) IS NOT NULL
                                    THEN ST_GeomFromGeoJSON(CAST(:geometry_json AS TEXT))
                                ELSE ST_GeomFromText(CAST(:geometry_wkt AS TEXT))
                            END,
                            4326
                        )
                    )
                    """
                ),
                {
                    "source": row.get("source") or "MANUAL_URBAN",
                    "external_id": row.get("external_id"),
                    "name": row.get("name"),
                    "mode": row.get("mode"),
                    "operator": row.get("operator"),
                    "is_accessible": row.get("is_accessible"),
                    "metadata_json": json.dumps(row.get("metadata_json") or {}, ensure_ascii=False),
                    "geometry_json": row.get("geometry_json"),
                    "geometry_wkt": row.get("geometry_wkt"),
                },
            )
    return len(unique_rows)


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
        parsed_reference_period = _parse_reference_year(reference_period)
        _territory_id, municipality_name, bbox = _resolve_municipality_context(settings)
    except Exception as exc:
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
        dataset = _resolve_dataset(
            reference_period=parsed_reference_period,
            bbox=bbox,
            client=client,
        )
        if dataset is None:
            warnings.append("No urban transport source available (remote catalog and manual directories failed).")
            elapsed = time.perf_counter() - started_at
            if not dry_run:
                with session_scope(settings) as session:
                    upsert_pipeline_run(
                        session=session,
                        run_id=run_id,
                        job_name=JOB_NAME,
                        source=SOURCE,
                        dataset=DATASET_NAME,
                        wave=WAVE,
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
                                "name": "urban_transport_stops_source_resolved",
                                "status": "warn",
                                "details": warnings[-1],
                                "observed_value": 0,
                                "threshold_value": 1,
                            },
                            {
                                "name": "urban_transport_stops_rows_loaded",
                                "status": "warn",
                                "details": "0 transport rows loaded because no source was available.",
                                "observed_value": 0,
                                "threshold_value": 1,
                            },
                        ],
                    )
            return {
                "job": JOB_NAME,
                "status": "blocked",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": 0,
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
            }

        rows, raw_bytes, source_suffix, source_type, source_uri, source_file_name, source_warnings = dataset
        warnings.extend(source_warnings)
        rows_extracted = len(rows)

        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": JOB_NAME,
                "status": "success" if rows else "blocked",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": rows_extracted,
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "preview": {
                    "municipality_name": municipality_name,
                    "source_type": source_type,
                    "source_uri": source_uri,
                    "source_file_name": source_file_name,
                    "bbox": {
                        "minx": bbox[0],
                        "miny": bbox[1],
                        "maxx": bbox[2],
                        "maxy": bbox[3],
                    },
                    "first_row": rows[0] if rows else None,
                },
            }

        rows_written = _replace_transport_rows(settings, rows)
        checks = [
            {
                "name": "urban_transport_stops_source_resolved",
                "status": "pass" if source_type in {"remote", "manual"} else "warn",
                "details": f"Source type resolved as {source_type}.",
                "observed_value": 1 if source_type in {"remote", "manual"} else 0,
                "threshold_value": 1,
            },
            {
                "name": "urban_transport_stops_rows_loaded",
                "status": "pass" if rows_written > 0 else "warn",
                "details": f"{rows_written} transport rows written into map.urban_transport_stop.",
                "observed_value": rows_written,
                "threshold_value": 1,
            },
            {
                "name": "urban_transport_stops_mode_rows",
                "status": "pass" if sum(1 for row in rows if row.get("mode")) > 0 else "warn",
                "details": "Transport rows should include mode metadata.",
                "observed_value": sum(1 for row in rows if row.get("mode")),
                "threshold_value": 1,
            },
        ]

        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=parsed_reference_period,
            raw_bytes=raw_bytes,
            extension=source_suffix if source_suffix else ".json",
            uri=source_uri,
            territory_scope="urban",
            dataset_version="urban-transport-v1",
            checks=checks,
            notes="Urban transport ingestion with bbox-scoped extraction and map upsert.",
            run_id=run_id,
            tables_written=["map.urban_transport_stop"] if rows_written > 0 else [],
            rows_written=(
                [{"table": "map.urban_transport_stop", "rows": rows_written}]
                if rows_written > 0
                else []
            ),
        )

        status = "success" if rows_written > 0 else "blocked"
        finished_at_utc = datetime.now(UTC)
        with session_scope(settings) as session:
            upsert_pipeline_run(
                session=session,
                run_id=run_id,
                job_name=JOB_NAME,
                source=SOURCE,
                dataset=DATASET_NAME,
                wave=WAVE,
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
                },
            )
            replace_pipeline_checks_from_dicts(session=session, run_id=run_id, checks=checks)

        elapsed = time.perf_counter() - started_at
        logger.info(
            "Urban transport job finished.",
            run_id=run_id,
            status=status,
            rows_extracted=rows_extracted,
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
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
                        job_name=JOB_NAME,
                        source=SOURCE,
                        dataset=DATASET_NAME,
                        wave=WAVE,
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
                                "name": "urban_transport_stops_job_exception",
                                "status": "fail",
                                "details": f"Urban transport connector failed with exception: {exc}",
                                "observed_value": 1,
                                "threshold_value": 0,
                            }
                        ],
                    )
            except Exception:
                logger.exception("Could not persist failed pipeline run in ops tables.", run_id=run_id)

        logger.exception(
            "Urban transport job failed.",
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

