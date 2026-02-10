from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from pipelines.common.quality_thresholds import QualityThresholds, as_float


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
        "education_inep_fetch",
        "health_datasus_fetch",
        "finance_siconfi_fetch",
        "labor_mte_fetch",
    )

    for job_name in jobs:
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
        results.append(
            CheckResult(
                name=f"mvp3_pipeline_run_{job_name}",
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
