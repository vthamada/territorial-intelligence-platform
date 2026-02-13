from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.routes_map import (
    get_map_layer_metadata,
    get_map_layers,
    get_map_layers_coverage,
)
from app.schemas.map import (
    MapLayerMetadataResponse,
    MapLayerReadinessItem,
    MapLayersReadinessResponse,
    MapLayersCoverageResponse,
    MapLayersResponse,
)

router = APIRouter(prefix="/territory/layers", tags=["territory-layers"])


@router.get("/catalog", response_model=MapLayersResponse)
def get_territory_layers_catalog() -> MapLayersResponse:
    return get_map_layers()


@router.get("/coverage", response_model=MapLayersCoverageResponse)
def get_territory_layers_coverage(
    metric: str | None = Query(default=None),
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> MapLayersCoverageResponse:
    return get_map_layers_coverage(metric=metric, period=period, db=db)


@router.get("/{layer_id}/metadata", response_model=MapLayerMetadataResponse)
def get_territory_layer_metadata(layer_id: str) -> MapLayerMetadataResponse:
    return get_map_layer_metadata(layer_id=layer_id)


@router.get("/readiness", response_model=MapLayersReadinessResponse)
def get_territory_layers_readiness(
    metric: str | None = Query(default=None),
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> MapLayersReadinessResponse:
    catalog = get_map_layers()
    coverage = get_map_layers_coverage(metric=metric, period=period, db=db)

    latest_quality_run = db.execute(
        text(
            """
            SELECT run_id::text AS run_id, started_at_utc
            FROM ops.pipeline_runs
            WHERE job_name = 'quality_suite'
            ORDER BY started_at_utc DESC, run_id DESC
            LIMIT 1
            """
        )
    ).mappings().first()

    checks_by_name: dict[str, dict] = {}
    quality_run_id: str | None = None
    quality_run_started_at_utc: datetime | None = None
    if latest_quality_run is not None:
        quality_run_id = str(latest_quality_run["run_id"])
        quality_run_started_at_utc = latest_quality_run["started_at_utc"]
        check_rows = db.execute(
            text(
                """
                SELECT check_name, status, details, observed_value, threshold_value
                FROM ops.pipeline_checks
                WHERE run_id = CAST(:run_id AS uuid)
                  AND (
                    check_name LIKE 'map_layer_rows_%'
                    OR check_name LIKE 'map_layer_geometry_ratio_%'
                  )
                ORDER BY check_id DESC
                """
            ),
            {"run_id": quality_run_id},
        ).mappings().all()
        checks_by_name = {str(row["check_name"]): dict(row) for row in check_rows}

    catalog_by_id = {item.id: item for item in catalog.items}
    items: list[MapLayerReadinessItem] = []
    for coverage_item in coverage.items:
        layer = catalog_by_id[coverage_item.layer_id]
        row_check_name = f"map_layer_rows_{coverage_item.territory_level}"
        geometry_check_name = f"map_layer_geometry_ratio_{coverage_item.territory_level}"
        row_check = checks_by_name.get(row_check_name)
        geometry_check = checks_by_name.get(geometry_check_name)

        row_status = str(row_check["status"]) if row_check else None
        geometry_status = str(geometry_check["status"]) if geometry_check else None
        statuses = [status for status in (row_status, geometry_status) if status]

        if "fail" in statuses:
            readiness_status = "fail"
            readiness_reason = "Check de qualidade com falha para a camada."
        elif "warn" in statuses:
            readiness_status = "warn"
            readiness_reason = "Camada com aviso de qualidade; revisar cobertura e geometria."
        elif coverage_item.is_ready:
            readiness_status = "pass"
            readiness_reason = None
        else:
            readiness_status = "pending"
            readiness_reason = coverage_item.notes or "Camada ainda sem cobertura operacional completa."

        items.append(
            MapLayerReadinessItem(
                layer=layer,
                coverage=coverage_item,
                readiness_status=readiness_status,
                readiness_reason=readiness_reason,
                row_check=row_check,
                geometry_check=geometry_check,
            )
        )

    return MapLayersReadinessResponse(
        generated_at_utc=datetime.now(tz=UTC),
        metric=metric,
        period=period,
        quality_run_id=quality_run_id,
        quality_run_started_at_utc=quality_run_started_at_utc,
        items=items,
    )
