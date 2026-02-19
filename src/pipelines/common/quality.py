from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from pipelines.common.quality_thresholds import QualityThresholds, as_float

_INDICATOR_SOURCE_MAP: tuple[tuple[str, str], ...] = (
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
