from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import geopandas as gpd
from shapely import make_valid, wkb
from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run

JOB_NAME = "ibge_geometries_fetch"
SOURCE = "IBGE"
DATASET_NAME = "ibge_malhas_territoriais"
MUNICIPALITY_DATASET = "ibge_malha_municipal"
DISTRICT_DATASET = "ibge_malha_distrital"
SECTOR_DATASET = "ibge_malha_setor_censitario"

MUNICIPALITY_URL_TEMPLATE = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_municipais/municipio_2024/UFs/{uf}/{uf}_Municipios_2024.zip"
)
DISTRICT_URL_TEMPLATE = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/"
    "distritos/shp/UF/{uf}_distritos_CD2022.zip"
)
SECTOR_URL_TEMPLATE = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/"
    "setores/shp/UF/{uf}_setores_CD2022.zip"
)


def _normalize_text(value: str) -> str:
    return value.strip().casefold()


def _resolve_scope_context(settings: Settings) -> tuple[str, str]:
    with session_scope(settings) as session:
        row = session.execute(
            text(
                """
                SELECT name, uf
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
        return "Diamantina", "MG"
    return str(row[0]).strip() or "Diamantina", (str(row[1]).strip().upper() or "MG")


def _select_municipality_feature(
    municipalities_gdf: gpd.GeoDataFrame,
    *,
    municipality_code: str,
    municipality_name: str,
    warnings: list[str],
) -> Any:
    by_code = municipalities_gdf[
        municipalities_gdf["CD_MUN"].astype(str).str.strip() == municipality_code
    ]
    if not by_code.empty:
        if len(by_code) > 1:
            warnings.append(
                f"Multiple municipality polygons found for code {municipality_code}; using the first."
            )
        return by_code.iloc[0]

    by_name = municipalities_gdf[
        municipalities_gdf["NM_MUN"].astype(str).map(_normalize_text) == _normalize_text(municipality_name)
    ]
    if not by_name.empty:
        warnings.append(
            (
                f"Municipality code {municipality_code} not found in malha municipal. "
                f"Using municipality name match '{municipality_name}'."
            )
        )
        if len(by_name) > 1:
            warnings.append(
                f"Multiple municipality polygons found for name '{municipality_name}'; using the first."
            )
        return by_name.iloc[0]

    raise ValueError(
        (
            f"Municipality not found in IBGE malha. "
            f"code={municipality_code}, name='{municipality_name}'."
        )
    )


def _normalize_geometry(raw_geometry: Any) -> tuple[Any | None, bool]:
    if raw_geometry is None or raw_geometry.is_empty:
        return None, False
    if raw_geometry.is_valid:
        return raw_geometry, False
    repaired = make_valid(raw_geometry)
    if repaired is None or repaired.is_empty:
        return None, True
    return repaired, True


def _to_target_crs(gdf: gpd.GeoDataFrame, target_epsg: int) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        return gdf.set_crs(epsg=target_epsg, allow_override=True)
    current_epsg = gdf.crs.to_epsg()
    if current_epsg == target_epsg:
        return gdf
    return gdf.to_crs(epsg=target_epsg)


def _empty_geodataframe(target_epsg: int) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=f"EPSG:{target_epsg}")


def _upsert_territory(
    *,
    session: Any,
    level: str,
    parent_territory_id: str | None,
    canonical_key: str,
    source_entity_id: str,
    ibge_geocode: str,
    name: str,
    normalized_name: str,
    uf: str,
    municipality_ibge_code: str,
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
                municipality_ibge_code
            )
            VALUES (
                CAST(:level AS silver.territory_level),
                CAST(:parent_territory_id AS uuid),
                :canonical_key,
                'IBGE',
                :source_entity_id,
                :ibge_geocode,
                '',
                '',
                :name,
                :normalized_name,
                :uf,
                :municipality_ibge_code
            )
            ON CONFLICT (level, ibge_geocode, tse_zone, tse_section, municipality_ibge_code)
            DO UPDATE SET
                parent_territory_id = EXCLUDED.parent_territory_id,
                canonical_key = EXCLUDED.canonical_key,
                source_system = EXCLUDED.source_system,
                source_entity_id = EXCLUDED.source_entity_id,
                name = EXCLUDED.name,
                normalized_name = EXCLUDED.normalized_name,
                uf = EXCLUDED.uf,
                updated_at = NOW()
            RETURNING territory_id::text
            """
        ),
        {
            "level": level,
            "parent_territory_id": parent_territory_id,
            "canonical_key": canonical_key,
            "source_entity_id": source_entity_id,
            "ibge_geocode": ibge_geocode,
            "name": name,
            "normalized_name": normalized_name,
            "uf": uf,
            "municipality_ibge_code": municipality_ibge_code,
        },
    ).first()
    if row is None:
        raise RuntimeError(f"Could not upsert territory level={level} code={ibge_geocode}.")
    return str(row[0])


def _update_geometry(
    *,
    session: Any,
    territory_id: str,
    geometry: Any,
    epsg: int,
    metadata: dict[str, Any],
) -> None:
    session.execute(
        text(
            """
            UPDATE silver.dim_territory
            SET
                geometry = ST_MakeValid(ST_SetSRID(ST_GeomFromWKB(:geometry_wkb), :epsg)),
                metadata = COALESCE(metadata, '{}'::jsonb) || CAST(:metadata_json AS jsonb),
                updated_at = NOW()
            WHERE territory_id = CAST(:territory_id AS uuid)
            """
        ),
        {
            "territory_id": territory_id,
            "geometry_wkb": wkb.dumps(geometry, hex=False),
            "epsg": epsg,
            "metadata_json": json.dumps(metadata),
        },
    )


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
        municipality_name, uf = _resolve_scope_context(settings)
        municipality_url = MUNICIPALITY_URL_TEMPLATE.format(uf=uf)
        district_url = DISTRICT_URL_TEMPLATE.format(uf=uf)
        sector_url = SECTOR_URL_TEMPLATE.format(uf=uf)

        municipality_bytes, _ = client.download_bytes(
            municipality_url,
            expected_content_types=["zip", "octet-stream"],
            min_bytes=1024,
        )
        district_bytes: bytes | None
        sector_bytes: bytes | None
        try:
            district_bytes, _ = client.download_bytes(
                district_url,
                expected_content_types=["zip", "octet-stream"],
                min_bytes=1024,
            )
        except Exception:
            district_bytes = None
            warnings.append(f"District malha unavailable for UF {uf}; continuing without district geometry.")
        try:
            sector_bytes, _ = client.download_bytes(
                sector_url,
                expected_content_types=["zip", "octet-stream"],
                min_bytes=1024,
            )
        except Exception:
            sector_bytes = None
            warnings.append(
                f"Census sector malha unavailable for UF {uf}; continuing without sector geometry."
            )

        tmp_dir = Path("tmp") / "ibge_geometries" / run_id
        tmp_dir.mkdir(parents=True, exist_ok=True)
        muni_zip = tmp_dir / "municipios.zip"
        dist_zip = tmp_dir / "distritos.zip"
        set_zip = tmp_dir / "setores.zip"
        muni_zip.write_bytes(municipality_bytes)
        if district_bytes is not None:
            dist_zip.write_bytes(district_bytes)
        if sector_bytes is not None:
            set_zip.write_bytes(sector_bytes)

        municipalities_gdf = _to_target_crs(
            gpd.read_file(muni_zip, engine="pyogrio"),
            settings.crs_epsg,
        )
        municipality_feature = _select_municipality_feature(
            municipalities_gdf,
            municipality_code=settings.municipality_ibge_code,
            municipality_name=municipality_name,
            warnings=warnings,
        )

        source_municipality_code = str(municipality_feature["CD_MUN"]).strip()
        source_municipality_name = str(municipality_feature["NM_MUN"]).strip()
        if source_municipality_code != settings.municipality_ibge_code:
            warnings.append(
                (
                    f"Configured MUNICIPALITY_IBGE_CODE={settings.municipality_ibge_code} differs from "
                    f"official malha code {source_municipality_code}."
                )
            )
        municipality_geometry, municipality_repaired = _normalize_geometry(municipality_feature.geometry)
        if municipality_geometry is None:
            raise ValueError("Municipality geometry is empty after validation.")
        if municipality_repaired:
            warnings.append("Municipality geometry was invalid and required make_valid.")

        if district_bytes is not None:
            districts_gdf = _to_target_crs(
                gpd.read_file(
                    dist_zip,
                    engine="pyogrio",
                    where=f"CD_MUN = '{source_municipality_code}'",
                ),
                settings.crs_epsg,
            )
        else:
            districts_gdf = _empty_geodataframe(settings.crs_epsg)

        if sector_bytes is not None:
            sectors_gdf = _to_target_crs(
                gpd.read_file(
                    set_zip,
                    engine="pyogrio",
                    where=f"CD_MUN = '{source_municipality_code}'",
                ),
                settings.crs_epsg,
            )
        else:
            sectors_gdf = _empty_geodataframe(settings.crs_epsg)

        extracted_rows = 1 + len(districts_gdf) + len(sectors_gdf)
        if dry_run:
            elapsed = time.perf_counter() - started_at
            return {
                "job": JOB_NAME,
                "status": "success",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": extracted_rows,
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "bronze_preview": [
                    {
                        "source": SOURCE,
                        "dataset": MUNICIPALITY_DATASET,
                        "reference_period": reference_period,
                        "uri": municipality_url,
                        "size_bytes": len(municipality_bytes),
                    },
                    *(
                        [
                            {
                                "source": SOURCE,
                                "dataset": DISTRICT_DATASET,
                                "reference_period": reference_period,
                                "uri": district_url,
                                "size_bytes": len(district_bytes),
                            }
                        ]
                        if district_bytes is not None
                        else []
                    ),
                    *(
                        [
                            {
                                "source": SOURCE,
                                "dataset": SECTOR_DATASET,
                                "reference_period": reference_period,
                                "uri": sector_url,
                                "size_bytes": len(sector_bytes),
                            }
                        ]
                        if sector_bytes is not None
                        else []
                    ),
                ],
                "details": {
                    "source_municipality_code": source_municipality_code,
                    "districts_found": len(districts_gdf),
                    "sectors_found": len(sectors_gdf),
                },
            }

        with session_scope(settings) as session:
            municipality_id = _upsert_territory(
                session=session,
                level="municipality",
                parent_territory_id=None,
                canonical_key=f"municipality:ibge:{source_municipality_code}",
                source_entity_id=source_municipality_code,
                ibge_geocode=source_municipality_code,
                name=source_municipality_name,
                normalized_name=_normalize_text(source_municipality_name),
                uf=uf,
                municipality_ibge_code=settings.municipality_ibge_code,
            )
            _update_geometry(
                session=session,
                territory_id=municipality_id,
                geometry=municipality_geometry,
                epsg=settings.crs_epsg,
                metadata={
                    "geometry_source": "IBGE malhas territoriais",
                    "geometry_dataset": MUNICIPALITY_DATASET,
                    "geometry_reference_period": reference_period,
                },
            )

            district_ids: dict[str, str] = {}
            districts_written = 0
            district_invalid_repaired = 0
            for _, row in districts_gdf.iterrows():
                district_code = str(row["CD_DIST"]).strip()
                district_name = str(row["NM_DIST"]).strip()
                if not district_code or not district_name:
                    continue

                geometry, repaired = _normalize_geometry(row.geometry)
                if geometry is None:
                    warnings.append(f"Skipped district {district_code}: empty geometry.")
                    continue
                if repaired:
                    district_invalid_repaired += 1

                district_id = _upsert_territory(
                    session=session,
                    level="district",
                    parent_territory_id=municipality_id,
                    canonical_key=f"district:ibge:{district_code}",
                    source_entity_id=district_code,
                    ibge_geocode=district_code,
                    name=district_name,
                    normalized_name=_normalize_text(district_name),
                    uf=uf,
                    municipality_ibge_code=settings.municipality_ibge_code,
                )
                _update_geometry(
                    session=session,
                    territory_id=district_id,
                    geometry=geometry,
                    epsg=settings.crs_epsg,
                    metadata={
                        "geometry_source": "IBGE malhas territoriais",
                        "geometry_dataset": DISTRICT_DATASET,
                        "geometry_reference_period": reference_period,
                    },
                )
                district_ids[district_code] = district_id
                districts_written += 1

            sectors_written = 0
            sector_invalid_repaired = 0
            missing_parent_count = 0
            for _, row in sectors_gdf.iterrows():
                sector_code = str(row["CD_SETOR"]).strip()
                district_code = str(row["CD_DIST"]).strip()
                if not sector_code:
                    continue

                geometry, repaired = _normalize_geometry(row.geometry)
                if geometry is None:
                    warnings.append(f"Skipped sector {sector_code}: empty geometry.")
                    continue
                if repaired:
                    sector_invalid_repaired += 1

                parent_id = district_ids.get(district_code)
                if parent_id is None:
                    parent_id = municipality_id
                    missing_parent_count += 1

                sector_id = _upsert_territory(
                    session=session,
                    level="census_sector",
                    parent_territory_id=parent_id,
                    canonical_key=f"census_sector:ibge:{sector_code}",
                    source_entity_id=sector_code,
                    ibge_geocode=sector_code,
                    name=f"Setor {sector_code}",
                    normalized_name=f"setor {sector_code}".lower(),
                    uf=uf,
                    municipality_ibge_code=settings.municipality_ibge_code,
                )
                _update_geometry(
                    session=session,
                    territory_id=sector_id,
                    geometry=geometry,
                    epsg=settings.crs_epsg,
                    metadata={
                        "geometry_source": "IBGE malhas territoriais",
                        "geometry_dataset": SECTOR_DATASET,
                        "geometry_reference_period": reference_period,
                    },
                )
                sectors_written += 1

            if district_invalid_repaired > 0:
                warnings.append(
                    f"{district_invalid_repaired} district geometries were invalid and required make_valid."
                )
            if sector_invalid_repaired > 0:
                warnings.append(
                    f"{sector_invalid_repaired} sector geometries were invalid and required make_valid."
                )
            if missing_parent_count > 0:
                warnings.append(
                    (
                        f"{missing_parent_count} sectors had no district parent in the current run; "
                        "parent fallback used municipality."
                    )
                )

        checks = [
            {
                "name": "municipality_geometry_non_empty",
                "status": "pass",
                "details": f"Municipality {source_municipality_code} geometry loaded.",
            },
            {
                "name": "district_geometries_count",
                "status": "pass" if districts_written > 0 else "warn",
                "details": f"{districts_written} district geometries loaded.",
            },
            {
                "name": "sector_geometries_count",
                "status": "pass" if sectors_written > 0 else "warn",
                "details": f"{sectors_written} sector geometries loaded.",
            },
        ]

        municipality_artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=MUNICIPALITY_DATASET,
            reference_period=reference_period,
            raw_bytes=municipality_bytes,
            extension=".zip",
            uri=municipality_url,
            territory_scope="municipality",
            dataset_version="malha_municipal_2024",
            checks=checks,
            notes="Municipality geometry import into silver.dim_territory.geometry",
            run_id=run_id,
            tables_written=["silver.dim_territory"],
            rows_written=[{"table": "silver.dim_territory", "rows": 1}],
        )
        district_artifact = (
            persist_raw_bytes(
                settings=settings,
                source=SOURCE,
                dataset=DISTRICT_DATASET,
                reference_period=reference_period,
                raw_bytes=district_bytes,
                extension=".zip",
                uri=district_url,
                territory_scope="district",
                dataset_version="malha_distrital_2022",
                checks=checks,
                notes="District geometries import into silver.dim_territory.geometry",
                run_id=run_id,
                tables_written=["silver.dim_territory"],
                rows_written=[{"table": "silver.dim_territory", "rows": districts_written}],
            )
            if district_bytes is not None
            else None
        )
        sector_artifact = (
            persist_raw_bytes(
                settings=settings,
                source=SOURCE,
                dataset=SECTOR_DATASET,
                reference_period=reference_period,
                raw_bytes=sector_bytes,
                extension=".zip",
                uri=sector_url,
                territory_scope="census_sector",
                dataset_version="malha_setor_2022",
                checks=checks,
                notes="Census sector geometries import into silver.dim_territory.geometry",
                run_id=run_id,
                tables_written=["silver.dim_territory"],
                rows_written=[{"table": "silver.dim_territory", "rows": sectors_written}],
            )
            if sector_bytes is not None
            else None
        )

        rows_written = 1 + districts_written + sectors_written
        finished_at_utc = datetime.now(UTC)
        with session_scope(settings) as session:
            upsert_pipeline_run(
                session=session,
                run_id=run_id,
                job_name=JOB_NAME,
                source=SOURCE,
                dataset=DATASET_NAME,
                wave="MVP-1",
                reference_period=reference_period,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
                status="success",
                rows_extracted=extracted_rows,
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=municipality_artifact.local_path.as_posix(),
                manifest_path=municipality_artifact.manifest_path.as_posix(),
                checksum_sha256=municipality_artifact.checksum_sha256,
                details={
                    "source_municipality_code": source_municipality_code,
                    "districts_found": len(districts_gdf),
                    "districts_loaded": districts_written,
                    "sectors_found": len(sectors_gdf),
                    "sectors_loaded": sectors_written,
                    "artifacts": [
                        artifact_to_dict(municipality_artifact),
                        *([artifact_to_dict(district_artifact)] if district_artifact is not None else []),
                        *([artifact_to_dict(sector_artifact)] if sector_artifact is not None else []),
                    ],
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
            "IBGE geometries job finished.",
            run_id=run_id,
            rows_extracted=extracted_rows,
            rows_written=rows_written,
            duration_seconds=round(elapsed, 2),
        )
        return {
            "job": JOB_NAME,
            "status": "success",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": extracted_rows,
            "rows_written": rows_written,
            "warnings": warnings,
            "errors": [],
            "bronze": [
                artifact_to_dict(municipality_artifact),
                *([artifact_to_dict(district_artifact)] if district_artifact is not None else []),
                *([artifact_to_dict(sector_artifact)] if sector_artifact is not None else []),
            ],
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
                        wave="MVP-1",
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

        try:
            logger.exception(
                "IBGE geometries job failed.",
                run_id=run_id,
                duration_seconds=round(elapsed, 2),
            )
        except Exception:
            logger.error(
                "IBGE geometries job failed (logging fallback).",
                run_id=run_id,
                duration_seconds=round(elapsed, 2),
                error=str(exc).encode("ascii", errors="backslashreplace").decode("ascii"),
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
