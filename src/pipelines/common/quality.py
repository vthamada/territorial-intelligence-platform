from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from pipelines.common.quality_thresholds import QualityThresholds, as_float

_INDICATOR_SOURCE_MAP: tuple[tuple[str, str], ...] = (
    ("datasus", "DATASUS"),
    ("inep", "INEP"),
    ("siconfi", "SICONFI"),
    ("mte", "MTE"),
    ("tse", "TSE"),
    ("sidra", "SIDRA"),
    ("senatran", "SENATRAN"),
    ("sejusp_mg", "SEJUSP_MG"),
    ("siops", "SIOPS"),
    ("snis", "SNIS"),
    ("inmet", "INMET"),
    ("inpe_queimadas", "INPE_QUEIMADAS"),
    ("ana", "ANA"),
    ("anatel", "ANATEL"),
    ("aneel", "ANEEL"),
    ("suasweb", "SUASWEB"),
    ("cneas", "CNEAS"),
    ("cecad", "CECAD"),
    ("censo_suas", "CENSO_SUAS"),
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    details: str
    observed_value: Any
    threshold_value: Any | None = None


def _scalar(session: Session, sql: str, params: dict[str, Any] | None = None) -> Any:
    return session.execute(text(sql), params or {}).scalar_one()


def _missing_ratio(session: Session, table_name: str, condition_sql: str) -> float:
    total = _scalar(session, f"SELECT COUNT(*) FROM {table_name}")
    if total == 0:
        return 0.0
    missing = _scalar(session, f"SELECT COUNT(*) FROM {table_name} WHERE {condition_sql}")
    return as_float(missing) / as_float(total)


def _normalize_type_name(value: str) -> str:
    normalized = " ".join(value.strip().lower().split())
    normalized = normalized.replace("pg_catalog.", "")
    normalized = normalized.replace("public.", "")
    return normalized


def _is_type_compatible(expected_type: str, actual_type: str) -> bool:
    expected = _normalize_type_name(expected_type)
    actual = _normalize_type_name(actual_type)

    if expected == actual:
        return True
    if expected == "text" and actual in {"character varying", "varchar", "text"}:
        return True
    if expected == "numeric" and actual in {
        "numeric",
        "double precision",
        "real",
        "integer",
        "bigint",
        "smallint",
    }:
        return True
    if expected == "integer" and actual in {"integer", "smallint", "bigint"}:
        return True
    if expected.startswith("geometry("):
        if not actual.startswith("geometry("):
            return False
        expected_tokens = expected.removeprefix("geometry(").removesuffix(")").split(",")
        actual_tokens = actual.removeprefix("geometry(").removesuffix(")").split(",")
        expected_subtype = expected_tokens[0].strip() if expected_tokens else ""
        actual_subtype = actual_tokens[0].strip() if actual_tokens else ""
        expected_srid = expected_tokens[1].strip() if len(expected_tokens) > 1 else ""
        actual_srid = actual_tokens[1].strip() if len(actual_tokens) > 1 else ""
        if expected_subtype and actual_subtype and expected_subtype != actual_subtype:
            return False
        if expected_srid and actual_srid and expected_srid != actual_srid:
            return False
        return True
    return False


def check_dim_territory(
    session: Session,
    municipality_code: str,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    municipality_count = _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM silver.dim_territory
        WHERE level = 'municipality'
          AND municipality_ibge_code = :code
          AND ibge_geocode = :code
        """,
        {"code": municipality_code},
    )
    results.append(
        CheckResult(
            name="municipality_exists",
            status="pass" if municipality_count > 0 else "fail",
            details=f"Expected municipality {municipality_code} to exist.",
            observed_value=municipality_count,
            threshold_value=1,
        )
    )

    min_district_count = thresholds.get("dim_territory", "min_district_count", fallback=1)
    district_count = _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM silver.dim_territory
        WHERE level = 'district'
          AND municipality_ibge_code = :code
        """,
        {"code": municipality_code},
    )
    results.append(
        CheckResult(
            name="districts_count",
            status="pass" if district_count >= min_district_count else "warn",
            details="Expected at least one district for municipality scope.",
            observed_value=district_count,
            threshold_value=min_district_count,
        )
    )

    geometry_scope = session.execute(
        text(
            """
            SELECT
                COUNT(*) AS total_rows,
                COUNT(*) FILTER (WHERE geometry IS NULL) AS missing_geometry_rows,
                COUNT(*) FILTER (
                    WHERE geometry IS NOT NULL AND ST_IsEmpty(geometry)
                ) AS empty_geometry_rows,
                COUNT(*) FILTER (
                    WHERE geometry IS NOT NULL AND NOT ST_IsValid(geometry)
                ) AS invalid_geometry_rows
            FROM silver.dim_territory
            WHERE municipality_ibge_code = :code
              AND level IN ('municipality', 'district', 'census_sector')
            """
        ),
        {"code": municipality_code},
    ).mappings().one()

    total_rows = int(geometry_scope["total_rows"])
    missing_rows = int(geometry_scope["missing_geometry_rows"])
    empty_rows = int(geometry_scope["empty_geometry_rows"])
    invalid_rows = int(geometry_scope["invalid_geometry_rows"])

    if total_rows == 0:
        missing_ratio = 0.0
    else:
        missing_ratio = as_float(missing_rows) / as_float(total_rows)

    max_geometry_missing_ratio = thresholds.get(
        "dim_territory",
        "max_geometry_missing_ratio",
        fallback=0.0,
    )
    results.append(
        CheckResult(
            name="geometry_missing_ratio",
            status="pass" if missing_ratio <= max_geometry_missing_ratio else "fail",
            details="Geometry should be populated for municipality/district/census_sector levels.",
            observed_value=missing_ratio,
            threshold_value=max_geometry_missing_ratio,
        )
    )

    max_empty_geometry_rows = thresholds.get("dim_territory", "max_empty_geometry_rows", fallback=0)
    results.append(
        CheckResult(
            name="geometry_empty_rows",
            status="pass" if empty_rows <= max_empty_geometry_rows else "fail",
            details="Geometry must not be empty.",
            observed_value=empty_rows,
            threshold_value=max_empty_geometry_rows,
        )
    )

    max_invalid_geometry_rows = thresholds.get(
        "dim_territory",
        "max_invalid_geometry_rows",
        fallback=0,
    )
    results.append(
        CheckResult(
            name="geometry_invalid_rows",
            status="pass" if invalid_rows <= max_invalid_geometry_rows else "fail",
            details="Geometry must be valid when present.",
            observed_value=invalid_rows,
            threshold_value=max_invalid_geometry_rows,
        )
    )

    return results


def check_dim_territory_electoral_zone_integrity(
    session: Session,
    municipality_code: str,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    min_electoral_zone_count = thresholds.get(
        "dim_territory",
        "min_electoral_zone_count",
        fallback=1,
    )
    electoral_zone_count = _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM silver.dim_territory
        WHERE level = 'electoral_zone'
          AND municipality_ibge_code = :code
        """,
        {"code": municipality_code},
    )
    results.append(
        CheckResult(
            name="electoral_zone_count",
            status="pass" if electoral_zone_count >= min_electoral_zone_count else "warn",
            details="Expected electoral zones for municipality scope.",
            observed_value=electoral_zone_count,
            threshold_value=min_electoral_zone_count,
        )
    )

    max_electoral_zone_orphans = thresholds.get(
        "dim_territory",
        "max_electoral_zone_orphans",
        fallback=0,
    )
    electoral_zone_orphans = _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM silver.dim_territory z
        LEFT JOIN silver.dim_territory p ON p.territory_id = z.parent_territory_id
        WHERE z.level = 'electoral_zone'
          AND z.municipality_ibge_code = :code
          AND (
                z.parent_territory_id IS NULL
                OR p.level::text <> 'municipality'
              )
        """,
        {"code": municipality_code},
    )
    results.append(
        CheckResult(
            name="electoral_zone_orphans",
            status="pass" if electoral_zone_orphans <= max_electoral_zone_orphans else "fail",
            details="Electoral zones must have municipality parent_territory_id.",
            observed_value=electoral_zone_orphans,
            threshold_value=max_electoral_zone_orphans,
        )
    )

    max_missing_canonical_key = thresholds.get(
        "dim_territory",
        "max_electoral_zone_missing_canonical_key",
        fallback=0,
    )
    missing_canonical_key = _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM silver.dim_territory
        WHERE level = 'electoral_zone'
          AND municipality_ibge_code = :code
          AND (canonical_key IS NULL OR TRIM(canonical_key) = '')
        """,
        {"code": municipality_code},
    )
    results.append(
        CheckResult(
            name="electoral_zone_missing_canonical_key",
            status="pass" if missing_canonical_key <= max_missing_canonical_key else "fail",
            details="Electoral zones must have canonical_key.",
            observed_value=missing_canonical_key,
            threshold_value=max_missing_canonical_key,
        )
    )
    return results


def check_map_layers(
    session: Session,
    municipality_code: str,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    layer_specs = (
        ("municipality", True, "municipal"),
        ("district", True, "distrital"),
        ("census_sector", False, "setorial"),
        ("electoral_zone", False, "zona eleitoral"),
        ("electoral_section", False, "secao eleitoral"),
    )

    for level, is_required, label in layer_specs:
        min_rows = thresholds.get("map_layers", f"min_rows_{level}", fallback=1)
        min_geometry_ratio = thresholds.get(
            "map_layers",
            f"min_geometry_ratio_{level}",
            fallback=1.0 if is_required else 0.0,
        )

        total_rows = _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM silver.dim_territory
            WHERE municipality_ibge_code = :code
              AND level::text = :level
            """,
            {"code": municipality_code, "level": level},
        )
        rows_with_geometry = _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM silver.dim_territory
            WHERE municipality_ibge_code = :code
              AND level::text = :level
              AND geometry IS NOT NULL
            """,
            {"code": municipality_code, "level": level},
        )

        total_rows = int(total_rows)
        rows_with_geometry = int(rows_with_geometry)
        geometry_ratio = (as_float(rows_with_geometry) / as_float(total_rows)) if total_rows > 0 else 0.0

        row_status = "pass" if total_rows >= min_rows else ("fail" if is_required else "warn")
        geometry_status = "pass" if geometry_ratio >= min_geometry_ratio else ("fail" if is_required else "warn")

        results.append(
            CheckResult(
                name=f"map_layer_rows_{level}",
                status=row_status,
                details=f"Expected minimum territorial rows for {label} layer.",
                observed_value=total_rows,
                threshold_value=min_rows,
            )
        )
        results.append(
            CheckResult(
                name=f"map_layer_geometry_ratio_{level}",
                status=geometry_status,
                details=f"Expected minimum geometry coverage ratio for {label} layer.",
                observed_value=geometry_ratio,
                threshold_value=min_geometry_ratio,
            )
        )
    return results


def check_fact_electorate(
    session: Session,
    municipality_code: str,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    max_negative_rows = thresholds.get("fact_electorate", "max_negative_rows", fallback=0)
    negative_voters = _scalar(
        session,
        "SELECT COUNT(*) FROM silver.fact_electorate WHERE voters < 0",
    )
    results.append(
        CheckResult(
            name="voters_non_negative",
            status="pass" if negative_voters <= max_negative_rows else "fail",
            details="voters must be >= 0.",
            observed_value=negative_voters,
            threshold_value=max_negative_rows,
        )
    )

    max_missing_ratio = thresholds.get("fact_electorate", "max_missing_ratio", fallback=0)
    year_missing_ratio = _missing_ratio(
        session,
        "silver.fact_electorate",
        "reference_year IS NULL",
    )
    results.append(
        CheckResult(
            name="reference_year_missing_ratio",
            status="pass" if year_missing_ratio <= max_missing_ratio else "fail",
            details="reference_year must be populated.",
            observed_value=year_missing_ratio,
            threshold_value=max_missing_ratio,
        )
    )

    min_rows_after_filter = thresholds.get("fact_electorate", "min_rows_after_filter", fallback=1)
    rows_after_filter = _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM silver.fact_electorate fe
        JOIN silver.dim_territory dt ON dt.territory_id = fe.territory_id
        WHERE dt.municipality_ibge_code = :code
        """,
        {"code": municipality_code},
    )
    results.append(
        CheckResult(
            name="rows_after_municipality_filter",
            status="pass" if rows_after_filter >= min_rows_after_filter else "warn",
            details="Rows after municipality filter should be greater than configured minimum.",
            observed_value=rows_after_filter,
            threshold_value=min_rows_after_filter,
        )
    )
    return results


def check_fact_election_result(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    max_negative_rows = thresholds.get("fact_election_result", "max_negative_rows", fallback=0)
    negative_values = _scalar(
        session,
        "SELECT COUNT(*) FROM silver.fact_election_result WHERE value < 0",
    )
    results.append(
        CheckResult(
            name="result_non_negative",
            status="pass" if negative_values <= max_negative_rows else "fail",
            details="result value must be >= 0.",
            observed_value=negative_values,
            threshold_value=max_negative_rows,
        )
    )

    max_missing_ratio = thresholds.get("fact_election_result", "max_missing_ratio", fallback=0)
    null_year_ratio = _missing_ratio(
        session,
        "silver.fact_election_result",
        "election_year IS NULL",
    )
    results.append(
        CheckResult(
            name="election_year_missing_ratio",
            status="pass" if null_year_ratio <= max_missing_ratio else "fail",
            details="election_year must be populated.",
            observed_value=null_year_ratio,
            threshold_value=max_missing_ratio,
        )
    )

    territory_missing_ratio = _missing_ratio(
        session,
        "silver.fact_election_result",
        "territory_id IS NULL",
    )
    results.append(
        CheckResult(
            name="territory_id_missing_ratio",
            status="pass" if territory_missing_ratio <= max_missing_ratio else "fail",
            details="territory_id must be resolved.",
            observed_value=territory_missing_ratio,
            threshold_value=max_missing_ratio,
        )
    )
    return results


def check_fact_indicator(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    max_missing_ratio = thresholds.get("fact_indicator", "max_missing_ratio", fallback=0)

    missing_indicator_code_ratio = _missing_ratio(
        session,
        "silver.fact_indicator",
        "indicator_code IS NULL OR indicator_code = ''",
    )
    results.append(
        CheckResult(
            name="indicator_code_missing_ratio",
            status="pass" if missing_indicator_code_ratio <= max_missing_ratio else "fail",
            details="indicator_code must be populated.",
            observed_value=missing_indicator_code_ratio,
            threshold_value=max_missing_ratio,
        )
    )

    missing_reference_period_ratio = _missing_ratio(
        session,
        "silver.fact_indicator",
        "reference_period IS NULL OR reference_period = ''",
    )
    results.append(
        CheckResult(
            name="reference_period_missing_ratio",
            status="pass" if missing_reference_period_ratio <= max_missing_ratio else "fail",
            details="reference_period must be populated.",
            observed_value=missing_reference_period_ratio,
            threshold_value=max_missing_ratio,
        )
    )

    missing_value_ratio = _missing_ratio(
        session,
        "silver.fact_indicator",
        "value IS NULL",
    )
    results.append(
        CheckResult(
            name="value_missing_ratio",
            status="pass" if missing_value_ratio <= max_missing_ratio else "fail",
            details="value must be populated.",
            observed_value=missing_value_ratio,
            threshold_value=max_missing_ratio,
        )
    )

    missing_territory_ratio = _missing_ratio(
        session,
        "silver.fact_indicator",
        "territory_id IS NULL",
    )
    results.append(
        CheckResult(
            name="territory_id_missing_ratio",
            status="pass" if missing_territory_ratio <= max_missing_ratio else "fail",
            details="territory_id must be resolved.",
            observed_value=missing_territory_ratio,
            threshold_value=max_missing_ratio,
        )
    )

    max_source_probe_rows = thresholds.get(
        "fact_indicator",
        "max_source_probe_rows",
        fallback=0,
    )
    source_probe_rows = _scalar(
        session,
        """
        SELECT COUNT(*)
        FROM silver.fact_indicator
        WHERE indicator_code LIKE '%_SOURCE_PROBE'
        """,
    )
    results.append(
        CheckResult(
            name="source_probe_rows",
            status="pass" if source_probe_rows <= max_source_probe_rows else "warn",
            details=(
                "Legacy SOURCE_PROBE indicators should be zero after real connectors "
                "are stabilized."
            ),
            observed_value=source_probe_rows,
            threshold_value=max_source_probe_rows,
        )
    )
    return results


def check_fact_indicator_source_rows(
    session: Session,
    reference_period: str | None,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for source_key, source_name in _INDICATOR_SOURCE_MAP:
        min_rows = thresholds.get(
            "fact_indicator",
            f"min_rows_{source_key}",
            fallback=0,
        )
        rows = _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM silver.fact_indicator
            WHERE source = :source
              AND (
                    CAST(:reference_period AS TEXT) IS NULL
                    OR reference_period = CAST(:reference_period AS TEXT)
                  )
            """,
            {"source": source_name, "reference_period": reference_period},
        )
        results.append(
            CheckResult(
                name=f"source_rows_{source_key}",
                status="pass" if rows >= min_rows else "warn",
                details=(
                    f"Expected at least {min_rows} row(s) for source {source_name} "
                    f"in reference period {reference_period}."
                ),
                observed_value=rows,
                threshold_value=min_rows,
            )
        )

    return results


def check_fact_social_protection(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    min_rows = int(thresholds.get("fact_social_protection", "min_rows_after_filter", fallback=1))
    max_negative_rows = int(thresholds.get("fact_social_protection", "max_negative_rows", fallback=0))
    max_empty_metric_rows = int(thresholds.get("fact_social_protection", "max_empty_metric_rows", fallback=0))

    rows = int(_scalar(session, "SELECT COUNT(*) FROM silver.fact_social_protection") or 0)
    results.append(
        CheckResult(
            name="social_protection_rows_after_filter",
            status="pass" if rows >= min_rows else "warn",
            details="Social protection fact should contain at least one municipality row.",
            observed_value=rows,
            threshold_value=min_rows,
        )
    )

    negative_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM silver.fact_social_protection
            WHERE COALESCE(households_total, 0) < 0
               OR COALESCE(people_total, 0) < 0
               OR COALESCE(avg_income_per_capita, 0) < 0
               OR COALESCE(poverty_rate, 0) < 0
               OR COALESCE(extreme_poverty_rate, 0) < 0
            """,
        )
        or 0
    )
    results.append(
        CheckResult(
            name="social_protection_negative_rows",
            status="pass" if negative_rows <= max_negative_rows else "fail",
            details="Social protection metrics should not have negative values.",
            observed_value=negative_rows,
            threshold_value=max_negative_rows,
        )
    )

    empty_metric_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM silver.fact_social_protection
            WHERE households_total IS NULL
              AND people_total IS NULL
              AND avg_income_per_capita IS NULL
              AND poverty_rate IS NULL
              AND extreme_poverty_rate IS NULL
            """,
        )
        or 0
    )
    results.append(
        CheckResult(
            name="social_protection_empty_metric_rows",
            status="pass" if empty_metric_rows <= max_empty_metric_rows else "warn",
            details="Rows in social protection fact should have at least one populated metric.",
            observed_value=empty_metric_rows,
            threshold_value=max_empty_metric_rows,
        )
    )
    return results


def check_fact_social_assistance_network(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    min_rows = int(thresholds.get("fact_social_assistance_network", "min_rows_after_filter", fallback=1))
    max_negative_rows = int(thresholds.get("fact_social_assistance_network", "max_negative_rows", fallback=0))
    max_empty_metric_rows = int(
        thresholds.get("fact_social_assistance_network", "max_empty_metric_rows", fallback=0)
    )

    rows = int(_scalar(session, "SELECT COUNT(*) FROM silver.fact_social_assistance_network") or 0)
    results.append(
        CheckResult(
            name="social_assistance_network_rows_after_filter",
            status="pass" if rows >= min_rows else "warn",
            details="Social assistance network fact should contain at least one municipality row.",
            observed_value=rows,
            threshold_value=min_rows,
        )
    )

    negative_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM silver.fact_social_assistance_network
            WHERE COALESCE(cras_units, 0) < 0
               OR COALESCE(creas_units, 0) < 0
               OR COALESCE(social_units_total, 0) < 0
               OR COALESCE(workers_total, 0) < 0
               OR COALESCE(service_capacity_total, 0) < 0
            """,
        )
        or 0
    )
    results.append(
        CheckResult(
            name="social_assistance_network_negative_rows",
            status="pass" if negative_rows <= max_negative_rows else "fail",
            details="Social assistance network metrics should not have negative values.",
            observed_value=negative_rows,
            threshold_value=max_negative_rows,
        )
    )

    empty_metric_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM silver.fact_social_assistance_network
            WHERE cras_units IS NULL
              AND creas_units IS NULL
              AND social_units_total IS NULL
              AND workers_total IS NULL
              AND service_capacity_total IS NULL
            """,
        )
        or 0
    )
    results.append(
        CheckResult(
            name="social_assistance_network_empty_metric_rows",
            status="pass" if empty_metric_rows <= max_empty_metric_rows else "warn",
            details="Rows in social assistance network fact should have at least one populated metric.",
            observed_value=empty_metric_rows,
            threshold_value=max_empty_metric_rows,
        )
    )
    return results


def check_urban_domain(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    min_road_rows = int(thresholds.get("urban_domain", "min_road_rows", fallback=0))
    min_poi_rows = int(thresholds.get("urban_domain", "min_poi_rows", fallback=0))
    min_transport_rows = int(thresholds.get("urban_domain", "min_transport_rows", fallback=0))
    max_invalid_geometries = int(
        thresholds.get("urban_domain", "max_invalid_geometry_rows", fallback=0)
    )

    road_rows = int(_scalar(session, "SELECT COUNT(*) FROM map.urban_road_segment") or 0)
    road_invalid = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM map.urban_road_segment
            WHERE geom IS NULL
               OR ST_IsEmpty(geom)
               OR NOT ST_IsValid(geom)
            """,
        )
        or 0
    )
    poi_rows = int(_scalar(session, "SELECT COUNT(*) FROM map.urban_poi") or 0)
    poi_invalid = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM map.urban_poi
            WHERE geom IS NULL
               OR ST_IsEmpty(geom)
               OR NOT ST_IsValid(geom)
            """,
        )
        or 0
    )
    transport_rows = int(_scalar(session, "SELECT COUNT(*) FROM map.urban_transport_stop") or 0)
    transport_invalid = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM map.urban_transport_stop
            WHERE geom IS NULL
               OR ST_IsEmpty(geom)
               OR NOT ST_IsValid(geom)
            """,
        )
        or 0
    )

    results.append(
        CheckResult(
            name="urban_roads_rows_after_filter",
            status="pass" if road_rows >= min_road_rows else "warn",
            details="Urban roads layer should have rows loaded in map.urban_road_segment.",
            observed_value=road_rows,
            threshold_value=min_road_rows,
        )
    )
    results.append(
        CheckResult(
            name="urban_roads_invalid_geometry_rows",
            status="pass" if road_invalid <= max_invalid_geometries else "fail",
            details="Urban roads geometries must be valid.",
            observed_value=road_invalid,
            threshold_value=max_invalid_geometries,
        )
    )
    results.append(
        CheckResult(
            name="urban_pois_rows_after_filter",
            status="pass" if poi_rows >= min_poi_rows else "warn",
            details="Urban POIs layer should have rows loaded in map.urban_poi.",
            observed_value=poi_rows,
            threshold_value=min_poi_rows,
        )
    )
    results.append(
        CheckResult(
            name="urban_pois_invalid_geometry_rows",
            status="pass" if poi_invalid <= max_invalid_geometries else "fail",
            details="Urban POIs geometries must be valid.",
            observed_value=poi_invalid,
            threshold_value=max_invalid_geometries,
        )
    )
    results.append(
        CheckResult(
            name="urban_transport_stops_rows_after_filter",
            status="pass" if transport_rows >= min_transport_rows else "warn",
            details="Urban transport layer should have rows loaded in map.urban_transport_stop.",
            observed_value=transport_rows,
            threshold_value=min_transport_rows,
        )
    )
    results.append(
        CheckResult(
            name="urban_transport_stops_invalid_geometry_rows",
            status="pass" if transport_invalid <= max_invalid_geometries else "fail",
            details="Urban transport geometries must be valid.",
            observed_value=transport_invalid,
            threshold_value=max_invalid_geometries,
        )
    )
    return results


def check_environment_risk_aggregation(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    min_rows_district = int(thresholds.get("environment_risk", "min_rows_district", fallback=1))
    min_rows_census_sector = int(
        thresholds.get("environment_risk", "min_rows_census_sector", fallback=1)
    )
    min_distinct_periods = int(
        thresholds.get("environment_risk", "min_distinct_periods", fallback=1)
    )
    max_null_risk_rows = int(
        thresholds.get("environment_risk", "max_null_risk_score_rows", fallback=0)
    )
    max_null_hazard_rows = int(
        thresholds.get("environment_risk", "max_null_hazard_score_rows", fallback=0)
    )
    max_null_exposure_rows = int(
        thresholds.get("environment_risk", "max_null_exposure_score_rows", fallback=0)
    )

    district_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM map.v_environment_risk_aggregation
            WHERE territory_level = 'district'
            """,
        )
        or 0
    )
    census_sector_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM map.v_environment_risk_aggregation
            WHERE territory_level = 'census_sector'
            """,
        )
        or 0
    )
    distinct_periods = int(
        _scalar(
            session,
            """
            SELECT COUNT(DISTINCT reference_period)
            FROM map.v_environment_risk_aggregation
            """,
        )
        or 0
    )
    null_risk_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM map.v_environment_risk_aggregation
            WHERE environment_risk_score IS NULL
            """,
        )
        or 0
    )
    null_hazard_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM map.v_environment_risk_aggregation
            WHERE hazard_score IS NULL
            """,
        )
        or 0
    )
    null_exposure_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM map.v_environment_risk_aggregation
            WHERE exposure_score IS NULL
            """,
        )
        or 0
    )

    results.append(
        CheckResult(
            name="environment_risk_rows_district",
            status="pass" if district_rows >= min_rows_district else "warn",
            details="Environment risk aggregation should cover district level.",
            observed_value=district_rows,
            threshold_value=min_rows_district,
        )
    )
    results.append(
        CheckResult(
            name="environment_risk_rows_census_sector",
            status="pass" if census_sector_rows >= min_rows_census_sector else "warn",
            details="Environment risk aggregation should cover census sector level.",
            observed_value=census_sector_rows,
            threshold_value=min_rows_census_sector,
        )
    )
    results.append(
        CheckResult(
            name="environment_risk_distinct_periods",
            status="pass" if distinct_periods >= min_distinct_periods else "warn",
            details="Environment risk aggregation should preserve temporal coverage.",
            observed_value=distinct_periods,
            threshold_value=min_distinct_periods,
        )
    )
    results.append(
        CheckResult(
            name="environment_risk_null_score_rows",
            status="pass" if null_risk_rows <= max_null_risk_rows else "fail",
            details="Environment risk score must be populated.",
            observed_value=null_risk_rows,
            threshold_value=max_null_risk_rows,
        )
    )
    results.append(
        CheckResult(
            name="environment_risk_null_hazard_rows",
            status="pass" if null_hazard_rows <= max_null_hazard_rows else "fail",
            details="Environment hazard score must be populated.",
            observed_value=null_hazard_rows,
            threshold_value=max_null_hazard_rows,
        )
    )
    results.append(
        CheckResult(
            name="environment_risk_null_exposure_rows",
            status="pass" if null_exposure_rows <= max_null_exposure_rows else "fail",
            details="Environment exposure score must be populated.",
            observed_value=null_exposure_rows,
            threshold_value=max_null_exposure_rows,
        )
    )

    return results


def check_environment_risk_mart(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    min_rows_municipality = int(
        thresholds.get("environment_risk", "min_mart_rows_municipality", fallback=1)
    )
    min_rows_district = int(
        thresholds.get("environment_risk", "min_mart_rows_district", fallback=1)
    )
    min_rows_census_sector = int(
        thresholds.get("environment_risk", "min_mart_rows_census_sector", fallback=1)
    )
    min_distinct_periods = int(
        thresholds.get("environment_risk", "min_mart_distinct_periods", fallback=1)
    )
    max_null_score_rows = int(
        thresholds.get("environment_risk", "max_mart_null_score_rows", fallback=0)
    )

    municipality_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM gold.mart_environment_risk
            WHERE territory_level = 'municipality'
            """,
        )
        or 0
    )
    district_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM gold.mart_environment_risk
            WHERE territory_level = 'district'
            """,
        )
        or 0
    )
    census_sector_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM gold.mart_environment_risk
            WHERE territory_level = 'census_sector'
            """,
        )
        or 0
    )
    distinct_periods = int(
        _scalar(
            session,
            """
            SELECT COUNT(DISTINCT reference_period)
            FROM gold.mart_environment_risk
            """,
        )
        or 0
    )
    null_score_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM gold.mart_environment_risk
            WHERE environment_risk_score IS NULL
            """,
        )
        or 0
    )

    results.append(
        CheckResult(
            name="environment_risk_mart_rows_municipality",
            status="pass" if municipality_rows >= min_rows_municipality else "warn",
            details="Environment risk mart should cover municipality level.",
            observed_value=municipality_rows,
            threshold_value=min_rows_municipality,
        )
    )
    results.append(
        CheckResult(
            name="environment_risk_mart_rows_district",
            status="pass" if district_rows >= min_rows_district else "warn",
            details="Environment risk mart should cover district level.",
            observed_value=district_rows,
            threshold_value=min_rows_district,
        )
    )
    results.append(
        CheckResult(
            name="environment_risk_mart_rows_census_sector",
            status="pass" if census_sector_rows >= min_rows_census_sector else "warn",
            details="Environment risk mart should cover census sector level.",
            observed_value=census_sector_rows,
            threshold_value=min_rows_census_sector,
        )
    )
    results.append(
        CheckResult(
            name="environment_risk_mart_distinct_periods",
            status="pass" if distinct_periods >= min_distinct_periods else "warn",
            details="Environment risk mart should preserve temporal coverage.",
            observed_value=distinct_periods,
            threshold_value=min_distinct_periods,
        )
    )
    results.append(
        CheckResult(
            name="environment_risk_mart_null_score_rows",
            status="pass" if null_score_rows <= max_null_score_rows else "fail",
            details="Environment risk mart score must be populated.",
            observed_value=null_score_rows,
            threshold_value=max_null_score_rows,
        )
    )

    return results


def check_source_schema_contracts(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    min_active_coverage_pct = float(
        thresholds.get("schema_contracts", "min_active_coverage_pct", fallback=100.0)
    )
    max_missing_connectors = int(
        thresholds.get("schema_contracts", "max_missing_connectors", fallback=0)
    )

    expected_connectors = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM ops.connector_registry
            WHERE status::text IN ('implemented', 'partial')
              AND source <> 'INTERNAL'
              AND connector_name NOT IN ('quality_suite', 'dbt_build', 'tse_catalog_discovery')
            """,
        )
        or 0
    )
    covered_connectors = int(
        _scalar(
            session,
            """
            SELECT COUNT(DISTINCT cr.connector_name)
            FROM ops.connector_registry cr
            JOIN ops.v_source_schema_contracts_active ssc
              ON ssc.connector_name = cr.connector_name
            WHERE cr.status::text IN ('implemented', 'partial')
              AND cr.source <> 'INTERNAL'
              AND cr.connector_name NOT IN ('quality_suite', 'dbt_build', 'tse_catalog_discovery')
            """,
        )
        or 0
    )

    missing_connectors = max(expected_connectors - covered_connectors, 0)
    if expected_connectors == 0:
        coverage_pct = 0.0
    else:
        coverage_pct = round((covered_connectors / expected_connectors) * 100.0, 2)

    results.append(
        CheckResult(
            name="schema_contracts_active_coverage_pct",
            status="pass" if coverage_pct >= min_active_coverage_pct else "fail",
            details="Active schema contracts should cover all implemented/partial non-internal connectors.",
            observed_value=coverage_pct,
            threshold_value=min_active_coverage_pct,
        )
    )
    results.append(
        CheckResult(
            name="schema_contracts_missing_connectors",
            status="pass" if missing_connectors <= max_missing_connectors else "fail",
            details="Missing active schema contracts for connectors should be zero.",
            observed_value=missing_connectors,
            threshold_value=max_missing_connectors,
        )
    )
    return results


def check_source_schema_drift(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    max_missing_required_columns = int(
        thresholds.get("schema_drift", "max_missing_required_columns", fallback=0)
    )
    max_type_mismatch_columns = int(
        thresholds.get("schema_drift", "max_type_mismatch_columns", fallback=0)
    )
    max_connectors_with_drift = int(
        thresholds.get("schema_drift", "max_connectors_with_drift", fallback=0)
    )

    contracts = session.execute(
        text(
            """
            SELECT
                connector_name,
                target_table,
                required_columns,
                column_types
            FROM ops.v_source_schema_contracts_active
            ORDER BY connector_name
            """
        )
    ).mappings().all()

    connectors_with_drift = 0
    for contract in contracts:
        connector_name = str(contract["connector_name"])
        target_table = str(contract["target_table"])
        required_columns_raw = contract.get("required_columns")
        column_types_raw = contract.get("column_types")
        required_columns = (
            [str(item) for item in required_columns_raw]
            if isinstance(required_columns_raw, list)
            else []
        )
        column_types = (
            {str(key): str(value) for key, value in column_types_raw.items()}
            if isinstance(column_types_raw, dict)
            else {}
        )

        table_exists = bool(
            _scalar(
                session,
                "SELECT to_regclass(:target_table) IS NOT NULL",
                {"target_table": target_table},
            )
        )
        table_check_name = f"schema_drift_table_exists_{connector_name}"
        if not table_exists:
            connectors_with_drift += 1
            results.append(
                CheckResult(
                    name=table_check_name,
                    status="fail",
                    details=f"Target table '{target_table}' is missing for connector {connector_name}.",
                    observed_value=0,
                    threshold_value=1,
                )
            )
            results.append(
                CheckResult(
                    name=f"schema_drift_missing_required_columns_{connector_name}",
                    status="fail",
                    details=(
                        "Could not validate required columns because target table does not exist."
                    ),
                    observed_value=len(required_columns),
                    threshold_value=max_missing_required_columns,
                )
            )
            results.append(
                CheckResult(
                    name=f"schema_drift_type_mismatch_columns_{connector_name}",
                    status="fail",
                    details="Could not validate column types because target table does not exist.",
                    observed_value=len(column_types),
                    threshold_value=max_type_mismatch_columns,
                )
            )
            continue

        results.append(
            CheckResult(
                name=table_check_name,
                status="pass",
                details=f"Target table '{target_table}' exists.",
                observed_value=1,
                threshold_value=1,
            )
        )

        schema_name, table_name = target_table.split(".", 1)
        columns_rows = session.execute(
            text(
                """
                SELECT
                    a.attname AS column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) AS normalized_type
                FROM pg_catalog.pg_attribute a
                JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = :schema_name
                  AND c.relname = :table_name
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                """
            ),
            {"schema_name": schema_name, "table_name": table_name},
        ).mappings().all()
        actual_columns = {str(row["column_name"]) for row in columns_rows}
        actual_types = {
            str(row["column_name"]): str(row["normalized_type"]) for row in columns_rows
        }

        missing_required = sorted(set(required_columns) - actual_columns)
        missing_required_count = len(missing_required)
        missing_required_status = (
            "pass" if missing_required_count <= max_missing_required_columns else "fail"
        )
        if missing_required_status == "fail":
            connectors_with_drift += 1
        results.append(
            CheckResult(
                name=f"schema_drift_missing_required_columns_{connector_name}",
                status=missing_required_status,
                details=(
                    "Missing required column(s): "
                    + ", ".join(missing_required)
                    if missing_required
                    else "All required columns are present."
                ),
                observed_value=missing_required_count,
                threshold_value=max_missing_required_columns,
            )
        )

        type_mismatches: list[str] = []
        for column_name, expected_type in column_types.items():
            actual_type = actual_types.get(column_name)
            if not actual_type:
                continue
            if not _is_type_compatible(expected_type, actual_type):
                type_mismatches.append(f"{column_name}: expected={expected_type} actual={actual_type}")
        mismatch_count = len(type_mismatches)
        mismatch_status = "pass" if mismatch_count <= max_type_mismatch_columns else "fail"
        if mismatch_status == "fail" and missing_required_status != "fail":
            connectors_with_drift += 1
        results.append(
            CheckResult(
                name=f"schema_drift_type_mismatch_columns_{connector_name}",
                status=mismatch_status,
                details=(
                    "Type mismatch column(s): " + "; ".join(type_mismatches)
                    if type_mismatches
                    else "Column types are compatible with contract."
                ),
                observed_value=mismatch_count,
                threshold_value=max_type_mismatch_columns,
            )
        )

    results.append(
        CheckResult(
            name="schema_drift_connectors_with_issues",
            status="pass" if connectors_with_drift <= max_connectors_with_drift else "fail",
            details=(
                "Connectors with schema drift should stay within configured threshold."
            ),
            observed_value=connectors_with_drift,
            threshold_value=max_connectors_with_drift,
        )
    )
    return results


def check_fact_indicator_source_temporal_coverage(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    default_min_periods = int(
        thresholds.get("fact_indicator", "min_source_distinct_periods_default", fallback=1)
    )
    for source_key, source_name in _INDICATOR_SOURCE_MAP:
        min_periods = int(
            thresholds.get(
                "fact_indicator",
                f"min_periods_{source_key}",
                fallback=default_min_periods,
            )
        )
        distinct_periods = int(
            _scalar(
                session,
                """
                SELECT COUNT(DISTINCT reference_period)
                FROM silver.fact_indicator
                WHERE source = :source
                """,
                {"source": source_name},
            )
            or 0
        )
        results.append(
            CheckResult(
                name=f"source_periods_{source_key}",
                status="pass" if distinct_periods >= min_periods else "warn",
                details=(
                    f"Expected at least {min_periods} distinct period(s) for source {source_name}."
                ),
                observed_value=distinct_periods,
                threshold_value=min_periods,
            )
        )
    return results


def check_fact_electorate_temporal_coverage(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    min_distinct_years = int(
        thresholds.get("fact_electorate", "min_distinct_years", fallback=1)
    )
    distinct_years = int(
        _scalar(
            session,
            "SELECT COUNT(DISTINCT reference_year) FROM silver.fact_electorate",
        )
        or 0
    )
    results.append(
        CheckResult(
            name="electorate_distinct_years",
            status="pass" if distinct_years >= min_distinct_years else "warn",
            details=(
                "Electorate should keep historical coverage with at least "
                f"{min_distinct_years} distinct year(s)."
            ),
            observed_value=distinct_years,
            threshold_value=min_distinct_years,
        )
    )

    min_zone_rows = int(
        thresholds.get("fact_electorate", "min_electoral_zone_rows", fallback=0)
    )
    zone_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM silver.fact_electorate fe
            JOIN silver.dim_territory dt ON dt.territory_id = fe.territory_id
            WHERE dt.level::text = 'electoral_zone'
            """,
        )
        or 0
    )
    results.append(
        CheckResult(
            name="electorate_electoral_zone_rows",
            status="pass" if zone_rows >= min_zone_rows else "warn",
            details=(
                "Electorate zone-level coverage should satisfy minimum expected rows."
            ),
            observed_value=zone_rows,
            threshold_value=min_zone_rows,
        )
    )
    max_year_gap = int(thresholds.get("fact_electorate", "max_year_gap", fallback=2))
    observed_max_gap = int(
        _scalar(
            session,
            """
            WITH years AS (
                SELECT DISTINCT reference_year::int AS ref_year
                FROM silver.fact_electorate
                WHERE reference_year IS NOT NULL
            ),
            gaps AS (
                SELECT ref_year - LAG(ref_year) OVER (ORDER BY ref_year) AS year_gap
                FROM years
            )
            SELECT COALESCE(MAX(year_gap), 0)
            FROM gaps
            WHERE year_gap IS NOT NULL
            """,
        )
        or 0
    )
    results.append(
        CheckResult(
            name="electorate_max_year_gap",
            status="pass" if observed_max_gap <= max_year_gap else "warn",
            details="Electorate temporal series should avoid large year gaps.",
            observed_value=observed_max_gap,
            threshold_value=max_year_gap,
        )
    )
    return results


def check_fact_election_result_temporal_coverage(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    min_distinct_years = int(
        thresholds.get("fact_election_result", "min_distinct_years", fallback=1)
    )
    distinct_years = int(
        _scalar(
            session,
            "SELECT COUNT(DISTINCT election_year) FROM silver.fact_election_result",
        )
        or 0
    )
    results.append(
        CheckResult(
            name="election_result_distinct_years",
            status="pass" if distinct_years >= min_distinct_years else "warn",
            details=(
                "Election results should keep historical coverage with at least "
                f"{min_distinct_years} distinct year(s)."
            ),
            observed_value=distinct_years,
            threshold_value=min_distinct_years,
        )
    )

    min_zone_rows = int(
        thresholds.get("fact_election_result", "min_electoral_zone_rows", fallback=0)
    )
    zone_rows = int(
        _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM silver.fact_election_result fr
            JOIN silver.dim_territory dt ON dt.territory_id = fr.territory_id
            WHERE dt.level::text = 'electoral_zone'
            """,
        )
        or 0
    )
    results.append(
        CheckResult(
            name="election_result_electoral_zone_rows",
            status="pass" if zone_rows >= min_zone_rows else "warn",
            details=(
                "Election results zone-level coverage should satisfy minimum expected rows."
            ),
            observed_value=zone_rows,
            threshold_value=min_zone_rows,
        )
    )
    max_year_gap = int(thresholds.get("fact_election_result", "max_year_gap", fallback=2))
    observed_max_gap = int(
        _scalar(
            session,
            """
            WITH years AS (
                SELECT DISTINCT election_year::int AS ref_year
                FROM silver.fact_election_result
                WHERE election_year IS NOT NULL
            ),
            gaps AS (
                SELECT ref_year - LAG(ref_year) OVER (ORDER BY ref_year) AS year_gap
                FROM years
            )
            SELECT COALESCE(MAX(year_gap), 0)
            FROM gaps
            WHERE year_gap IS NOT NULL
            """,
        )
        or 0
    )
    results.append(
        CheckResult(
            name="election_result_max_year_gap",
            status="pass" if observed_max_gap <= max_year_gap else "warn",
            details="Election result temporal series should avoid large year gaps.",
            observed_value=observed_max_gap,
            threshold_value=max_year_gap,
        )
    )
    return results


def check_fact_indicator_temporal_coverage(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    min_distinct_periods = int(
        thresholds.get("fact_indicator", "min_distinct_periods", fallback=1)
    )
    distinct_periods = int(
        _scalar(
            session,
            "SELECT COUNT(DISTINCT reference_period) FROM silver.fact_indicator",
        )
        or 0
    )
    results.append(
        CheckResult(
            name="indicator_distinct_periods",
            status="pass" if distinct_periods >= min_distinct_periods else "warn",
            details=(
                "Indicators should keep historical coverage with at least "
                f"{min_distinct_periods} distinct period(s)."
            ),
            observed_value=distinct_periods,
            threshold_value=min_distinct_periods,
        )
    )

    level_thresholds = (
        ("municipality", "min_rows_level_municipality"),
        ("district", "min_rows_level_district"),
        ("census_sector", "min_rows_level_census_sector"),
    )
    for level, threshold_key in level_thresholds:
        min_rows = int(thresholds.get("fact_indicator", threshold_key, fallback=0))
        rows = int(
            _scalar(
                session,
                """
                SELECT COUNT(*)
                FROM silver.fact_indicator fi
                JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
                WHERE dt.level::text = :level
                """,
                {"level": level},
            )
            or 0
        )
        results.append(
            CheckResult(
                name=f"indicator_rows_level_{level}",
                status="pass" if rows >= min_rows else "warn",
                details=(
                    f"Indicator coverage for level '{level}' should satisfy minimum rows."
                ),
                observed_value=rows,
                threshold_value=min_rows,
            )
        )
    return results


def check_ops_pipeline_runs(
    session: Session,
    reference_period: str,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    min_successful_runs = thresholds.get(
        "ops_pipeline_runs",
        "min_successful_runs_per_job",
        fallback=1,
    )
    jobs = (
        ("education_inep_fetch", "MVP-3"),
        ("health_datasus_fetch", "MVP-3"),
        ("finance_siconfi_fetch", "MVP-3"),
        ("labor_mte_fetch", "MVP-3"),
        ("sidra_indicators_fetch", "MVP-4"),
        ("senatran_fleet_fetch", "MVP-4"),
        ("sejusp_public_safety_fetch", "MVP-4"),
        ("siops_health_finance_fetch", "MVP-4"),
        ("snis_sanitation_fetch", "MVP-4"),
        ("inmet_climate_fetch", "MVP-5"),
        ("inpe_queimadas_fetch", "MVP-5"),
        ("ana_hydrology_fetch", "MVP-5"),
        ("anatel_connectivity_fetch", "MVP-5"),
        ("aneel_energy_fetch", "MVP-5"),
        ("urban_roads_fetch", "MVP-7"),
        ("urban_pois_fetch", "MVP-7"),
        ("urban_transport_fetch", "MVP-7"),
    )

    for job_name, wave in jobs:
        sql = """
            SELECT COUNT(*)
            FROM ops.pipeline_runs
            WHERE job_name = :job_name
              AND reference_period = :reference_period
              AND status = 'success'
        """

        successful_runs = _scalar(
            session,
            sql,
            {"job_name": job_name, "reference_period": reference_period},
        )
        status = "pass" if successful_runs >= min_successful_runs else "warn"
        wave_token = wave.lower().replace("-", "")
        results.append(
            CheckResult(
                name=f"{wave_token}_pipeline_run_{job_name}",
                status=status,
                details=(
                    f"Expected at least {min_successful_runs} successful run(s) for "
                    f"{job_name} in reference period {reference_period}."
                ),
                observed_value=successful_runs,
                threshold_value=min_successful_runs,
            )
        )

    return results


# Backward-compatible aliases for previous Portuguese function names.
def check_dim_territorio(
    session: Session,
    municipality_code: str,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    return check_dim_territory(session, municipality_code, thresholds)


def check_fact_eleitorado(
    session: Session,
    municipality_code: str,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    return check_fact_electorate(session, municipality_code, thresholds)


def check_fact_resultado_eleitoral(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    return check_fact_election_result(session, thresholds)


def check_fact_indicador(
    session: Session,
    thresholds: QualityThresholds,
) -> list[CheckResult]:
    return check_fact_indicator(session, thresholds)
