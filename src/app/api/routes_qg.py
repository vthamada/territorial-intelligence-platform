from __future__ import annotations

from datetime import UTC
from datetime import datetime
import hashlib
from uuid import uuid4
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.territory_levels import normalize_level, to_external_level
from app.api.strategic_engine_config import (
    load_strategic_engine_config,
    score_to_status,
    status_impact,
)
from app.schemas.qg import (
    BriefEvidenceItem,
    BriefGenerateRequest,
    BriefGenerateResponse,
    ElectorateBreakdownItem,
    ElectorateMapItem,
    ElectorateMapResponse,
    ElectorateSummaryResponse,
    ExplainabilityCoverage,
    ExplainabilityTrail,
    EnvironmentRiskItem,
    EnvironmentRiskResponse,
    InsightHighlightItem,
    InsightHighlightsResponse,
    KpiOverviewItem,
    KpiOverviewResponse,
    MobilityAccessItem,
    MobilityAccessResponse,
    PriorityEvidence,
    PriorityItem,
    PriorityListResponse,
    PrioritySummaryResponse,
    QgMetadata,
    ScenarioSimulateRequest,
    ScenarioSimulateResponse,
    TerritoryCompareItem,
    TerritoryCompareResponse,
    TerritoryPeerItem,
    TerritoryPeersResponse,
    TerritoryProfileDomain,
    TerritoryProfileIndicator,
    TerritoryProfileResponse,
)

router = APIRouter(tags=["qg"])

_DOMAIN_CASE_SQL = """
CASE
    WHEN fi.source = 'DATASUS' THEN 'saude'
    WHEN fi.source = 'INEP' THEN 'educacao'
    WHEN fi.source = 'MTE' THEN 'trabalho'
    WHEN fi.source = 'SICONFI' THEN 'financas'
    WHEN fi.source = 'TSE' THEN 'eleitorado'
    WHEN fi.source = 'SIDRA' THEN 'socioeconomico'
    WHEN fi.source = 'SENATRAN' THEN 'mobilidade'
    WHEN fi.source = 'SEJUSP_MG' THEN 'seguranca'
    WHEN fi.source = 'SIOPS' THEN 'saude'
    WHEN fi.source = 'SNIS' THEN 'saneamento'
    WHEN fi.source = 'INMET' THEN 'clima'
    WHEN fi.source = 'INPE_QUEIMADAS' THEN 'meio_ambiente'
    WHEN fi.source = 'ANA' THEN 'recursos_hidricos'
    WHEN fi.source = 'ANATEL' THEN 'conectividade'
    WHEN fi.source = 'ANEEL' THEN 'energia'
    WHEN fi.source = 'CECAD' THEN 'assistencia_social'
    WHEN fi.source = 'CENSO_SUAS' THEN 'assistencia_social'
    WHEN fi.source = 'IBGE' THEN 'socioeconomico'
    ELSE 'geral'
END
"""

_ELECTORATE_BREAKDOWN_COLUMNS = {
    "sex": "fe.sex",
    "age": "fe.age_range",
    "education": "fe.education",
}
_MIN_ALLOWED_YEAR = 1900
_MAX_ALLOWED_YEAR_OFFSET = 1


# Sources classified as official government data.
_OFFICIAL_SOURCES = {
    "DATASUS", "INEP", "MTE", "SICONFI", "TSE", "IBGE", "SIDRA",
    "SIOPS", "SNIS", "ANA", "ANATEL", "ANEEL",
}
# Sources classified as proxy/estimated data.
_PROXY_SOURCES = {
    "SEJUSP_MG", "SENATRAN", "INMET", "INPE_QUEIMADAS",
}


def _classify_source(source_name: str) -> str:
    """Return 'oficial', 'proxy', or 'misto' based on source provenance."""
    if source_name in _OFFICIAL_SOURCES:
        return "oficial"
    if source_name in _PROXY_SOURCES:
        return "proxy"
    return "misto"


def _format_highlight_value(value: float, unit: str | None) -> str:
    """Format a numeric value with thousand separators and unit for user-facing text."""
    normalized_unit = (unit or "").strip().lower()
    if normalized_unit in ("brl", "r$"):
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if normalized_unit in ("%", "percent"):
        return f"{value:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
    if normalized_unit == "count":
        return f"{value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if normalized_unit == "ratio":
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    _UNIT_MAP = {"c": "°C", "mm": "mm", "m3/s": "m³/s", "m3s": "m³/s", "ha": "ha", "km": "km", "kwh": "kWh"}
    display_unit = _UNIT_MAP.get(normalized_unit, unit)
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if display_unit:
        return f"{formatted} {display_unit}"
    return formatted


_DOMAIN_INSIGHT_TEMPLATES: dict[str, str] = {
    "saude": "O indicador de saude {name} registrou {value} em {territory}, periodo {period}.",
    "educacao": "Na area de educacao, {name} atingiu {value} em {territory} ({period}).",
    "trabalho": "No mercado de trabalho, {name} ficou em {value} para {territory} ({period}).",
    "financas": "Nas financas publicas, {name} totalizou {value} em {territory} ({period}).",
    "eleitorado": "O perfil eleitoral de {territory} mostra {name} em {value} ({period}).",
    "conectividade": "Em conectividade, {name} alcancou {value} em {territory} ({period}).",
    "saneamento": "No saneamento basico, {name} ficou em {value} para {territory} ({period}).",
    "seguranca": "Em seguranca publica, {name} registrou {value} em {territory} ({period}).",
    "meio_ambiente": "Na area ambiental, {name} atingiu {value} em {territory} ({period}).",
    "socioeconomico": "No perfil socioeconomico, {name} ficou em {value} para {territory} ({period}).",
    "energia": "No setor de energia, {name} registrou {value} em {territory} ({period}).",
    "assistencia_social": "Na assistencia social, {name} atingiu {value} em {territory} ({period}).",
}
_DEFAULT_INSIGHT_TEMPLATE = "O indicador {name} apresentou valor de {value} em {territory} ({period})."


def _build_insight_explanation(row: dict[str, Any]) -> list[str]:
    """Build contextual insight explanation based on domain and status."""
    domain = str(row["domain"])
    template = _DOMAIN_INSIGHT_TEMPLATES.get(domain, _DEFAULT_INSIGHT_TEMPLATE)
    formatted_value = _format_highlight_value(float(row["value"]), row.get("unit"))
    period_str = str(row.get("reference_period", "-"))

    line1 = template.format(
        name=row["indicator_name"],
        value=formatted_value,
        territory=row["territory_name"],
        period=period_str,
    )

    status = row["status"]
    if status == "critical":
        line2 = f"Este indicador esta em faixa critica (score {row['score']:.0f}) e exige atencao imediata."
    elif status == "attention":
        line2 = f"Indicador na faixa de atencao (score {row['score']:.0f}), recomenda-se acompanhamento proximo."
    else:
        line2 = f"Indicador em faixa estavel (score {row['score']:.0f}), sem necessidade de acao urgente."

    line3 = f"Fonte: {row['source']}/{row.get('dataset', '-')}."
    return [line1, line2, line3]


def _qg_metadata(
    updated_at: datetime | None,
    notes: str | None = None,
    unit: str | None = None,
    source_classification: str | None = None,
    source_name: str = "silver.fact_indicator",
    config_version: str | None = None,
) -> QgMetadata:
    cfg = load_strategic_engine_config()
    return QgMetadata(
        source_name=source_name,
        updated_at=updated_at,
        coverage_note="territorial_aggregated",
        unit=unit,
        notes=notes,
        source_classification=source_classification or "misto",
        config_version=config_version or cfg.version,
    )


def _build_explainability_trail(row: dict[str, Any]) -> ExplainabilityTrail:
    trail_key = "|".join(
        [
            str(row.get("reference_period") or ""),
            str(row.get("territory_id") or ""),
            str(row.get("indicator_code") or ""),
            str(row.get("score_version") or ""),
            str(row.get("scoring_method") or ""),
        ]
    )
    trail_id = hashlib.sha1(trail_key.encode("utf-8")).hexdigest()[:16]

    coverage = None
    covered = row.get("coverage_covered_territories")
    total = row.get("coverage_total_territories")
    pct = row.get("coverage_pct")
    if covered is not None and total is not None and pct is not None:
        coverage = ExplainabilityCoverage(
            covered_territories=int(covered),
            total_territories=int(total),
            coverage_pct=float(pct),
        )

    return ExplainabilityTrail(
        trail_id=trail_id,
        score_version=str(row["score_version"]) if row.get("score_version") is not None else None,
        scoring_method=str(row["scoring_method"]) if row.get("scoring_method") is not None else None,
        driver_rank=int(row["driver_rank"]) if row.get("driver_rank") is not None else None,
        driver_total=int(row["driver_total"]) if row.get("driver_total") is not None else None,
        weighted_magnitude=float(row["weighted_magnitude"]) if row.get("weighted_magnitude") is not None else None,
        critical_threshold=float(row["critical_threshold"]) if row.get("critical_threshold") is not None else None,
        attention_threshold=float(row["attention_threshold"]) if row.get("attention_threshold") is not None else None,
        coverage=coverage,
    )


def _build_priority_rationale(row: dict[str, Any], trail: ExplainabilityTrail) -> list[str]:
    rationale = [
        f"Indicador {row['indicator_name']} com valor {row['value']:.2f}.",
        f"Dominio {row['domain']} em {row['territory_name']}.",
    ]
    if row["status"] == "critical":
        rationale.append("Criticidade alta dentro do recorte atual.")
    elif row["status"] == "attention":
        rationale.append("Indicador em faixa de atencao no recorte atual.")
    else:
        rationale.append("Indicador em faixa estavel no recorte atual.")

    if trail.driver_rank is not None and trail.driver_total is not None:
        rationale.append(
            f"Ranking explicavel no recorte: {trail.driver_rank}/{trail.driver_total}."
        )
    if trail.coverage is not None:
        rationale.append(
            "Cobertura territorial do dominio: "
            f"{trail.coverage.coverage_pct:.2f}% "
            f"({trail.coverage.covered_territories}/{trail.coverage.total_territories})."
        )
    return rationale


def _build_insight_deep_link(row: dict[str, Any], item_severity: str) -> str:
    period = str(row.get("reference_period") or "")
    level = str(row.get("territory_level") or "")
    domain = str(row.get("domain") or "")
    territory_id = str(row.get("territory_id") or "")
    indicator_code = str(row.get("indicator_code") or "")
    return (
        "/insights?"
        f"period={period}&level={level}&domain={domain}&severity={item_severity}"
        f"&territory_id={territory_id}&indicator_code={indicator_code}"
    )


def _fetch_priority_rows(
    db: Session,
    period: str | None,
    level: str | None,
    domain: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    query = text(
        """
        WITH base AS (
            SELECT
                mpd.territory_id::text AS territory_id,
                mpd.territory_name,
                mpd.territory_level::text AS territory_level,
                mpd.domain,
                mpd.indicator_code,
                mpd.indicator_name,
                mpd.value::double precision AS value,
                mpd.unit,
                mpd.reference_period,
                mpd.source,
                mpd.dataset,
                mpd.updated_at,
                mpd.score_version,
                mpd.config_version,
                mpd.scoring_method,
                mpd.critical_threshold::double precision AS critical_threshold,
                mpd.attention_threshold::double precision AS attention_threshold,
                mpd.domain_weight::double precision AS domain_weight,
                mpd.indicator_weight::double precision AS indicator_weight,
                mpd.weighted_magnitude::double precision AS weighted_magnitude,
                mpd.driver_rank::int AS driver_rank,
                mpd.driver_total::int AS driver_total,
                mpd.priority_score::double precision AS score,
                mpd.priority_status::text AS status
            FROM gold.mart_priority_drivers mpd
            WHERE (CAST(:period AS TEXT) IS NULL OR mpd.reference_period = CAST(:period AS TEXT))
              AND (CAST(:level AS TEXT) IS NULL OR mpd.territory_level::text = CAST(:level AS TEXT))
              AND (CAST(:domain AS TEXT) IS NULL OR mpd.domain = CAST(:domain AS TEXT))
        ),
        territory_totals AS (
            SELECT
                dt.level::text AS territory_level,
                COUNT(*)::int AS total_territories
            FROM silver.dim_territory dt
            GROUP BY dt.level::text
        ),
        domain_coverage AS (
            SELECT
                b.reference_period,
                b.territory_level,
                b.domain,
                COUNT(DISTINCT b.territory_id)::int AS covered_territories,
                COALESCE(tt.total_territories, 0)::int AS total_territories,
                CASE
                    WHEN COALESCE(tt.total_territories, 0) = 0 THEN 0.0
                    ELSE ROUND(
                        (COUNT(DISTINCT b.territory_id)::numeric / tt.total_territories::numeric) * 100,
                        2
                    )::double precision
                END AS coverage_pct
            FROM base b
            LEFT JOIN territory_totals tt
                ON tt.territory_level = b.territory_level
            GROUP BY b.reference_period, b.territory_level, b.domain, tt.total_territories
        )
        SELECT
            b.territory_id,
            b.territory_name,
            b.territory_level,
            b.domain,
            b.indicator_code,
            b.indicator_name,
            b.value,
            b.unit,
            b.reference_period,
            b.source,
            b.dataset,
            b.updated_at,
            b.score_version,
            b.config_version,
            b.scoring_method,
            b.critical_threshold,
            b.attention_threshold,
            b.domain_weight,
            b.indicator_weight,
            b.weighted_magnitude,
            b.driver_rank,
            b.driver_total,
            b.score,
            b.status,
            dc.covered_territories AS coverage_covered_territories,
            dc.total_territories AS coverage_total_territories,
            dc.coverage_pct
        FROM base b
        LEFT JOIN domain_coverage dc
            ON dc.reference_period = b.reference_period
           AND dc.territory_level = b.territory_level
           AND dc.domain = b.domain
        ORDER BY b.driver_rank ASC, b.territory_name ASC, b.indicator_code ASC
        LIMIT :limit
        """
    )
    return [dict(row) for row in db.execute(query, {"period": period, "level": level, "domain": domain, "limit": limit}).mappings().all()]


def _get_territory_context(db: Session, territory_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT
                territory_id::text AS territory_id,
                name AS territory_name,
                level::text AS territory_level
            FROM silver.dim_territory
            WHERE territory_id::text = :territory_id
            """
        ),
        {"territory_id": territory_id},
    ).mappings().first()
    return dict(row) if row else None


def _fetch_latest_indicator_rows(
    db: Session,
    territory_id: str,
    period: str | None,
) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            f"""
            WITH ranked AS (
                SELECT
                    {_DOMAIN_CASE_SQL} AS domain,
                    fi.indicator_code,
                    fi.indicator_name,
                    fi.value::double precision AS value,
                    fi.unit,
                    fi.reference_period,
                    fi.source,
                    fi.dataset,
                    fi.updated_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY fi.indicator_code
                        ORDER BY fi.reference_period DESC, fi.updated_at DESC
                    ) AS row_num
                FROM silver.fact_indicator fi
                WHERE fi.territory_id::text = :territory_id
                  AND (CAST(:period AS TEXT) IS NULL OR fi.reference_period = CAST(:period AS TEXT))
            )
            SELECT
                domain,
                indicator_code,
                indicator_name,
                value,
                unit,
                reference_period,
                source,
                dataset,
                updated_at
            FROM ranked
            WHERE row_num = 1
            ORDER BY domain ASC, indicator_code ASC
            """
        ),
        {"territory_id": territory_id, "period": period},
    ).mappings().all()
    return [dict(row) for row in rows]


def _score_to_status(score: float) -> str:
    return score_to_status(score)


def _score_from_rank(rank: int, total_items: int) -> float:
    if total_items <= 1:
        return 50.0
    return round((1 - ((rank - 1) / (total_items - 1))) * 100, 2)


def _status_impact(before: str, after: str) -> str:
    return status_impact(before, after)


def _previous_reference_period(period: str | None) -> str | None:
    if period is None:
        return None
    normalized = period.strip()
    if normalized.isdigit() and len(normalized) == 4:
        return str(int(normalized) - 1)
    return None


def _compute_trend(current_value: float, previous_value: float | None) -> str:
    """Return 'up', 'down' or 'stable' based on value delta."""
    if previous_value is None:
        return "stable"
    if current_value == previous_value:
        return "stable"
    delta_pct = ((current_value - previous_value) / abs(previous_value)) * 100 if previous_value != 0 else 0
    if delta_pct >= 2:
        return "up"
    if delta_pct <= -2:
        return "down"
    return "stable"


def _fetch_previous_values(
    db: Session,
    *,
    period: str,
    level: str | None,
) -> dict[tuple[str, str], float]:
    """Return {(territory_id, indicator_code): value} for the previous period."""
    prev_period = _previous_reference_period(period)
    if prev_period is None:
        return {}
    rows = db.execute(
        text(
            """
            SELECT
                dt.territory_id::text AS territory_id,
                fi.indicator_code,
                fi.value::double precision AS value
            FROM silver.fact_indicator fi
            JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
            WHERE fi.reference_period = CAST(:period AS TEXT)
              AND (CAST(:level AS TEXT) IS NULL OR dt.level::text = CAST(:level AS TEXT))
            """
        ),
        {"period": prev_period, "level": level},
    ).mappings().all()
    return {(str(row["territory_id"]), str(row["indicator_code"])): float(row["value"]) for row in rows}


def _fetch_territory_indicator_scores(
    db: Session,
    *,
    territory_id: str | None,
    period: str | None,
    level: str,
) -> list[dict[str, Any]]:
    cfg = load_strategic_engine_config()
    crit = cfg.scoring.critical_threshold
    att = cfg.scoring.attention_threshold
    rows = db.execute(
        text(
            f"""
            WITH latest AS (
                SELECT
                    dt.territory_id::text AS territory_id,
                    dt.name AS territory_name,
                    dt.level::text AS territory_level,
                    {_DOMAIN_CASE_SQL} AS domain,
                    fi.indicator_code,
                    fi.reference_period,
                    fi.value::double precision AS value,
                    fi.updated_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY dt.territory_id, fi.indicator_code
                        ORDER BY fi.reference_period DESC, fi.updated_at DESC
                    ) AS latest_row
                FROM silver.fact_indicator fi
                JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
                WHERE (CAST(:period AS TEXT) IS NULL OR fi.reference_period = CAST(:period AS TEXT))
                  AND dt.level::text = CAST(:level AS TEXT)
            ),
            filtered AS (
                SELECT *
                FROM latest
                WHERE latest_row = 1
            ),
            ranked AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY indicator_code
                        ORDER BY ABS(value) DESC, territory_name ASC
                    ) AS row_num,
                    COUNT(*) OVER (PARTITION BY indicator_code) AS total_rows
                FROM filtered
            ),
            scored AS (
                SELECT
                    *,
                    CASE
                        WHEN total_rows <= 1 THEN 50.0
                        ELSE ROUND((1 - ((row_num - 1)::numeric / (total_rows - 1))) * 100, 2)::double precision
                    END AS score
                FROM ranked
            )
            SELECT
                territory_id,
                territory_name,
                territory_level,
                domain,
                indicator_code,
                score,
                updated_at,
                CASE
                    WHEN score >= {crit} THEN 'critical'
                    WHEN score >= {att} THEN 'attention'
                    ELSE 'stable'
                END AS status
            FROM scored
            WHERE (CAST(:territory_id AS TEXT) IS NULL OR territory_id = CAST(:territory_id AS TEXT))
            """
        ),
        {"territory_id": territory_id, "period": period, "level": level},
    ).mappings().all()
    return [dict(row) for row in rows]


def _resolve_available_year(
    db: Session,
    *,
    level: str,
    requested_year: int | None,
    table_kind: str,
) -> int | None:
    max_allowed_year = datetime.now(UTC).year + _MAX_ALLOWED_YEAR_OFFSET

    if requested_year is not None and not (_MIN_ALLOWED_YEAR <= requested_year <= max_allowed_year):
        return None

    if table_kind == "electorate":
        if requested_year is not None:
            count = db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM silver.fact_electorate fe
                    JOIN silver.dim_territory dt ON dt.territory_id = fe.territory_id
                    WHERE dt.level::text = :level
                      AND fe.reference_year = :year
                    """
                ),
                {"level": level, "year": requested_year},
            ).scalar_one()
            return requested_year if count > 0 else None

        latest_year = db.execute(
            text(
                """
                SELECT MAX(fe.reference_year)
                FROM silver.fact_electorate fe
                JOIN silver.dim_territory dt ON dt.territory_id = fe.territory_id
                WHERE dt.level::text = :level
                  AND fe.reference_year BETWEEN :min_year AND :max_year
                """
            ),
            {"level": level, "min_year": _MIN_ALLOWED_YEAR, "max_year": max_allowed_year},
        ).scalar_one()
        if latest_year is None:
            return None
        latest_year_int = int(latest_year)
        if not (_MIN_ALLOWED_YEAR <= latest_year_int <= max_allowed_year):
            return None
        return latest_year_int

    if requested_year is not None:
        count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM silver.fact_election_result fr
                JOIN silver.dim_territory dt ON dt.territory_id = fr.territory_id
                WHERE dt.level::text = :level
                  AND fr.election_year = :year
                """
            ),
            {"level": level, "year": requested_year},
        ).scalar_one()
        return requested_year if count > 0 else None

    latest_year = db.execute(
        text(
            """
            SELECT MAX(fr.election_year)
            FROM silver.fact_election_result fr
            JOIN silver.dim_territory dt ON dt.territory_id = fr.territory_id
            WHERE dt.level::text = :level
              AND fr.election_year BETWEEN :min_year AND :max_year
            """
        ),
        {"level": level, "min_year": _MIN_ALLOWED_YEAR, "max_year": max_allowed_year},
    ).scalar_one()
    if latest_year is None:
        return None
    latest_year_int = int(latest_year)
    if not (_MIN_ALLOWED_YEAR <= latest_year_int <= max_allowed_year):
        return None
    return latest_year_int


def _resolve_outlier_electorate_storage_year(
    db: Session,
    *,
    level: str,
) -> int | None:
    max_allowed_year = datetime.now(UTC).year + _MAX_ALLOWED_YEAR_OFFSET
    outlier_year = db.execute(
        text(
            """
            SELECT MAX(fe.reference_year)
            FROM silver.fact_electorate fe
            JOIN silver.dim_territory dt ON dt.territory_id = fe.territory_id
            WHERE dt.level::text = :level
              AND fe.reference_year > :max_allowed_year
            """
        ),
        {"level": level, "max_allowed_year": max_allowed_year},
    ).scalar_one()
    if outlier_year is None:
        return None
    outlier_year_int = int(outlier_year)
    if outlier_year_int <= max_allowed_year:
        return None
    return outlier_year_int


def _resolve_electorate_year_binding(
    db: Session,
    *,
    level: str,
    requested_year: int | None,
) -> tuple[int | None, int | None, str | None]:
    resolved_year = _resolve_available_year(
        db,
        level=level,
        requested_year=requested_year,
        table_kind="electorate",
    )
    if resolved_year is not None:
        return resolved_year, resolved_year, None

    if requested_year is None:
        return None, None, None

    outlier_storage_year = _resolve_outlier_electorate_storage_year(db, level=level)
    if outlier_storage_year is None:
        return None, None, None

    outlier_count = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM silver.fact_electorate fe
            JOIN silver.dim_territory dt ON dt.territory_id = fe.territory_id
            WHERE dt.level::text = :level
              AND fe.reference_year = :storage_year
            """
        ),
        {"level": level, "storage_year": outlier_storage_year},
    ).scalar_one()
    if int(outlier_count) <= 0:
        return None, None, None

    return (
        requested_year,
        outlier_storage_year,
        (
            "electorate_outlier_year_fallback:"
            f"requested_year={requested_year},storage_year={outlier_storage_year}"
        ),
    )


def _fetch_electorate_breakdown(
    db: Session,
    *,
    level: str,
    year: int,
    breakdown_kind: str,
) -> list[ElectorateBreakdownItem]:
    column = _ELECTORATE_BREAKDOWN_COLUMNS[breakdown_kind]
    rows = db.execute(
        text(
            f"""
            SELECT
                COALESCE(NULLIF(TRIM({column}), ''), 'NAO_INFORMADO') AS label,
                SUM(fe.voters)::bigint AS voters
            FROM silver.fact_electorate fe
            JOIN silver.dim_territory dt ON dt.territory_id = fe.territory_id
            WHERE dt.level::text = :level
              AND fe.reference_year = :year
            GROUP BY label
            ORDER BY voters DESC, label ASC
            """
        ),
        {"level": level, "year": year},
    ).mappings().all()

    total_voters = sum(int(row["voters"]) for row in rows)
    if total_voters <= 0:
        return []

    return [
        ElectorateBreakdownItem(
            label=str(row["label"]),
            voters=int(row["voters"]),
            share_percent=round((int(row["voters"]) / total_voters) * 100, 6),
        )
        for row in rows
    ]


def _fetch_election_metrics(
    db: Session,
    *,
    level: str,
    year: int,
) -> dict[str, float]:
    rows = db.execute(
        text(
            """
            SELECT
                fr.metric,
                SUM(fr.value)::double precision AS total_value
            FROM silver.fact_election_result fr
            JOIN silver.dim_territory dt ON dt.territory_id = fr.territory_id
            WHERE dt.level::text = :level
              AND fr.election_year = :year
              AND fr.metric IN ('turnout', 'abstention', 'votes_blank', 'votes_null', 'votes_total')
            GROUP BY fr.metric
            """
        ),
        {"level": level, "year": year},
    ).mappings().all()
    return {str(row["metric"]): float(row["total_value"]) for row in rows}


def _resolve_effective_mobility_period(db: Session, requested_period: str | None) -> str | None:
    if requested_period:
        return requested_period
    row = db.execute(
        text(
            """
            SELECT MAX(reference_period) AS reference_period
            FROM gold.mart_mobility_access
            """
        )
    ).mappings().first()
    if not row or row.get("reference_period") is None:
        return None
    return str(row["reference_period"])


def _resolve_effective_environment_period(db: Session, requested_period: str | None) -> str | None:
    if requested_period:
        return requested_period
    row = db.execute(
        text(
            """
            SELECT MAX(reference_period) AS reference_period
            FROM gold.mart_environment_risk
            """
        )
    ).mappings().first()
    if not row or row.get("reference_period") is None:
        return None
    return str(row["reference_period"])


@router.get("/mobility/access", response_model=MobilityAccessResponse)
def get_mobility_access(
    period: str | None = Query(default=None),
    level: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),  # noqa: B008
) -> MobilityAccessResponse:
    level_en: str | None = None
    if level is not None:
        level_en = normalize_level(level)
        if level_en is None:
            raise HTTPException(status_code=422, detail=f"Invalid level '{level}'.")

    effective_period = _resolve_effective_mobility_period(db, period)
    if effective_period is None:
        return MobilityAccessResponse(
            period=period,
            level=to_external_level(level_en) if level_en else None,
            metadata=QgMetadata(
                source_name="gold.mart_mobility_access",
                updated_at=None,
                coverage_note="territorial_mobility",
                unit="score",
                notes="no_data_for_selected_filters",
                source_classification="misto",
                config_version=load_strategic_engine_config().version,
            ),
            items=[],
        )

    rows = db.execute(
        text(
            """
            SELECT
                reference_period,
                territory_id::text AS territory_id,
                territory_name,
                territory_level,
                municipality_ibge_code,
                road_segments_count,
                road_length_km,
                transport_stops_count,
                mobility_pois_count,
                fleet_total_effective,
                population_effective,
                vehicles_per_1k_pop,
                transport_stops_per_10k_pop,
                road_km_per_10k_pop,
                mobility_pois_per_10k_pop,
                mobility_access_score,
                mobility_access_deficit_score,
                priority_status,
                uses_proxy_allocation,
                allocation_method,
                refreshed_at_utc
            FROM gold.mart_mobility_access
            WHERE reference_period = CAST(:period AS TEXT)
              AND (CAST(:level AS TEXT) IS NULL OR territory_level = CAST(:level AS TEXT))
            ORDER BY mobility_access_deficit_score DESC, territory_name ASC
            LIMIT :limit
            """
        ),
        {"period": effective_period, "level": level_en, "limit": limit},
    ).mappings().all()

    if not rows:
        return MobilityAccessResponse(
            period=effective_period,
            level=to_external_level(level_en) if level_en else None,
            metadata=QgMetadata(
                source_name="gold.mart_mobility_access",
                updated_at=None,
                coverage_note="territorial_mobility",
                unit="score",
                notes="no_data_for_selected_filters",
                source_classification="misto",
                config_version=load_strategic_engine_config().version,
            ),
            items=[],
        )

    items = [
        MobilityAccessItem(
            reference_period=str(row["reference_period"]),
            territory_id=str(row["territory_id"]),
            territory_name=str(row["territory_name"]),
            territory_level=to_external_level(str(row["territory_level"])),
            municipality_ibge_code=row.get("municipality_ibge_code"),
            road_segments_count=int(row["road_segments_count"] or 0),
            road_length_km=float(row["road_length_km"] or 0.0),
            transport_stops_count=int(row["transport_stops_count"] or 0),
            mobility_pois_count=int(row["mobility_pois_count"] or 0),
            fleet_total_effective=float(row["fleet_total_effective"]) if row["fleet_total_effective"] is not None else None,
            population_effective=float(row["population_effective"]) if row["population_effective"] is not None else None,
            vehicles_per_1k_pop=float(row["vehicles_per_1k_pop"]) if row["vehicles_per_1k_pop"] is not None else None,
            transport_stops_per_10k_pop=float(row["transport_stops_per_10k_pop"])
            if row["transport_stops_per_10k_pop"] is not None
            else None,
            road_km_per_10k_pop=float(row["road_km_per_10k_pop"]) if row["road_km_per_10k_pop"] is not None else None,
            mobility_pois_per_10k_pop=float(row["mobility_pois_per_10k_pop"])
            if row["mobility_pois_per_10k_pop"] is not None
            else None,
            mobility_access_score=float(row["mobility_access_score"]),
            mobility_access_deficit_score=float(row["mobility_access_deficit_score"]),
            priority_status=str(row["priority_status"]),
            uses_proxy_allocation=bool(row["uses_proxy_allocation"]),
            allocation_method=str(row["allocation_method"]),
        )
        for row in rows
    ]

    updated_at = max((row.get("refreshed_at_utc") for row in rows), default=None)
    return MobilityAccessResponse(
        period=effective_period,
        level=to_external_level(level_en) if level_en else None,
        metadata=QgMetadata(
            source_name="gold.mart_mobility_access",
            updated_at=updated_at,
            coverage_note="territorial_mobility",
            unit="score",
            notes="mobility_access_mart_v1",
            source_classification="misto",
            config_version=load_strategic_engine_config().version,
        ),
        items=items,
    )


@router.get("/environment/risk", response_model=EnvironmentRiskResponse)
def get_environment_risk(
    period: str | None = Query(default=None),
    level: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),  # noqa: B008
) -> EnvironmentRiskResponse:
    level_en: str | None = None
    allowed_levels = {"municipality", "district", "census_sector"}
    if level is not None:
        level_en = normalize_level(level)
        if level_en is None or level_en not in allowed_levels:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid level '{level}'. Allowed values: municipality, district, census_sector.",
            )

    effective_period = _resolve_effective_environment_period(db, period)
    if effective_period is None:
        return EnvironmentRiskResponse(
            period=period,
            level=to_external_level(level_en) if level_en else None,
            metadata=QgMetadata(
                source_name="gold.mart_environment_risk",
                updated_at=None,
                coverage_note="territorial_environment_risk",
                unit="score",
                notes="no_data_for_selected_filters",
                source_classification="misto",
                config_version=load_strategic_engine_config().version,
            ),
            items=[],
        )

    rows = db.execute(
        text(
            """
            SELECT
                reference_period,
                territory_id::text AS territory_id,
                territory_name,
                territory_level,
                municipality_ibge_code,
                hazard_score,
                exposure_score,
                environment_risk_score,
                risk_percentile,
                risk_priority_rank,
                priority_status,
                area_km2,
                road_km,
                pois_count,
                transport_stops_count,
                road_density_km_per_km2,
                pois_per_km2,
                transport_stops_per_km2,
                population_effective,
                exposed_population_per_km2,
                uses_proxy_allocation,
                allocation_method,
                refreshed_at_utc
            FROM gold.mart_environment_risk
            WHERE reference_period = CAST(:period AS TEXT)
              AND (CAST(:level AS TEXT) IS NULL OR territory_level = CAST(:level AS TEXT))
            ORDER BY environment_risk_score DESC, territory_name ASC
            LIMIT :limit
            """
        ),
        {"period": effective_period, "level": level_en, "limit": limit},
    ).mappings().all()

    if not rows:
        return EnvironmentRiskResponse(
            period=effective_period,
            level=to_external_level(level_en) if level_en else None,
            metadata=QgMetadata(
                source_name="gold.mart_environment_risk",
                updated_at=None,
                coverage_note="territorial_environment_risk",
                unit="score",
                notes="no_data_for_selected_filters",
                source_classification="misto",
                config_version=load_strategic_engine_config().version,
            ),
            items=[],
        )

    items = [
        EnvironmentRiskItem(
            reference_period=str(row["reference_period"]),
            territory_id=str(row["territory_id"]),
            territory_name=str(row["territory_name"]),
            territory_level=to_external_level(str(row["territory_level"])),
            municipality_ibge_code=row.get("municipality_ibge_code"),
            hazard_score=float(row["hazard_score"]),
            exposure_score=float(row["exposure_score"]),
            environment_risk_score=float(row["environment_risk_score"]),
            risk_percentile=float(row["risk_percentile"]),
            risk_priority_rank=int(row["risk_priority_rank"]),
            priority_status=str(row["priority_status"]),
            area_km2=float(row["area_km2"]) if row["area_km2"] is not None else None,
            road_km=float(row["road_km"]) if row["road_km"] is not None else None,
            pois_count=int(row["pois_count"] or 0),
            transport_stops_count=int(row["transport_stops_count"] or 0),
            road_density_km_per_km2=float(row["road_density_km_per_km2"])
            if row["road_density_km_per_km2"] is not None
            else None,
            pois_per_km2=float(row["pois_per_km2"]) if row["pois_per_km2"] is not None else None,
            transport_stops_per_km2=float(row["transport_stops_per_km2"])
            if row["transport_stops_per_km2"] is not None
            else None,
            population_effective=float(row["population_effective"])
            if row["population_effective"] is not None
            else None,
            exposed_population_per_km2=float(row["exposed_population_per_km2"])
            if row["exposed_population_per_km2"] is not None
            else None,
            uses_proxy_allocation=bool(row["uses_proxy_allocation"]),
            allocation_method=str(row["allocation_method"]),
        )
        for row in rows
    ]

    updated_at = max((row.get("refreshed_at_utc") for row in rows), default=None)
    return EnvironmentRiskResponse(
        period=effective_period,
        level=to_external_level(level_en) if level_en else None,
        metadata=QgMetadata(
            source_name="gold.mart_environment_risk",
            updated_at=updated_at,
            coverage_note="territorial_environment_risk",
            unit="score",
            notes="environment_risk_mart_v1",
            source_classification="misto",
            config_version=load_strategic_engine_config().version,
        ),
        items=items,
    )


@router.get("/kpis/overview", response_model=KpiOverviewResponse)
def get_kpis_overview(
    period: str | None = Query(default=None),
    level: str | None = Query(default="municipality"),
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),  # noqa: B008
) -> KpiOverviewResponse:
    level_en = normalize_level(level)
    rows = db.execute(
        text(
            f"""
            SELECT
                {_DOMAIN_CASE_SQL} AS domain,
                fi.source,
                fi.dataset,
                fi.indicator_code,
                fi.indicator_name,
                AVG(fi.value)::double precision AS value,
                fi.unit,
                dt.level::text AS territory_level,
                MAX(fi.updated_at) AS updated_at
            FROM silver.fact_indicator fi
            JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
            WHERE (CAST(:period AS TEXT) IS NULL OR fi.reference_period = CAST(:period AS TEXT))
              AND (CAST(:level AS TEXT) IS NULL OR dt.level::text = CAST(:level AS TEXT))
            GROUP BY
                domain,
                fi.source,
                fi.dataset,
                fi.indicator_code,
                fi.indicator_name,
                fi.unit,
                dt.level::text
            ORDER BY MAX(fi.updated_at) DESC, fi.indicator_code ASC
            LIMIT :limit
            """
        ),
        {"period": period, "level": level_en, "limit": limit},
    ).mappings().all()

    payload_items = [
        KpiOverviewItem(
            domain=row["domain"],
            source=row.get("source"),
            dataset=row.get("dataset"),
            indicator_code=row["indicator_code"],
            indicator_name=row["indicator_name"],
            value=float(row["value"]),
            unit=row["unit"],
            delta=None,
            status="stable",
            territory_level=to_external_level(row["territory_level"]),
        )
        for row in rows
    ]

    updated_at = max((row["updated_at"] for row in rows), default=None)
    return KpiOverviewResponse(
        period=period,
        metadata=_qg_metadata(updated_at, notes="initial_qg_contract_v1"),
        items=payload_items,
    )


@router.get("/priority/list", response_model=PriorityListResponse)
def get_priority_list(
    period: str | None = Query(default=None),
    level: str | None = Query(default="municipality"),
    domain: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),  # noqa: B008
) -> PriorityListResponse:
    level_en = normalize_level(level)
    rows = _fetch_priority_rows(db=db, period=period, level=level_en, domain=domain, limit=limit)

    previous_values: dict[tuple[str, str], float] = {}
    if period:
        previous_values = _fetch_previous_values(db, period=period, level=level_en)

    items = []
    for row in rows:
        trail = _build_explainability_trail(row)
        rationale = _build_priority_rationale(row, trail)

        prev_val = previous_values.get((row["territory_id"], row["indicator_code"]))
        trend = _compute_trend(float(row["value"]), prev_val)

        items.append(
            PriorityItem(
                territory_id=row["territory_id"],
                territory_name=row["territory_name"],
                territory_level=to_external_level(row["territory_level"]),
                domain=row["domain"],
                indicator_code=row["indicator_code"],
                indicator_name=row["indicator_name"],
                value=float(row["value"]),
                unit=row["unit"],
                score=float(row["score"]),
                trend=trend,
                status=row["status"],
                rationale=rationale,
                evidence=PriorityEvidence(
                    indicator_code=row["indicator_code"],
                    reference_period=row["reference_period"],
                    source=row["source"],
                    dataset=row["dataset"],
                    updated_at=row.get("updated_at"),
                    score_version=str(row["score_version"]) if row.get("score_version") is not None else None,
                    scoring_method=str(row["scoring_method"]) if row.get("scoring_method") is not None else None,
                    domain_weight=float(row["domain_weight"]) if row.get("domain_weight") is not None else None,
                    indicator_weight=float(row["indicator_weight"]) if row.get("indicator_weight") is not None else None,
                ),
                explainability=trail,
            )
        )

    updated_at = max((row["updated_at"] for row in rows), default=None)
    score_version = next(
        (str(row["score_version"]) for row in rows if row.get("score_version") is not None),
        None,
    )
    return PriorityListResponse(
        period=period,
        level=to_external_level(level_en) if level_en else None,
        domain=domain,
        metadata=_qg_metadata(
            updated_at,
            notes="priority_drivers_mart_v1",
            source_name="gold.mart_priority_drivers",
            config_version=score_version,
        ),
        items=items,
    )


@router.get("/priority/summary", response_model=PrioritySummaryResponse)
def get_priority_summary(
    period: str | None = Query(default=None),
    level: str | None = Query(default="municipality"),
    domain: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),  # noqa: B008
) -> PrioritySummaryResponse:
    level_en = normalize_level(level)
    rows = _fetch_priority_rows(db=db, period=period, level=level_en, domain=domain, limit=limit)

    by_status: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    top_territories: list[str] = []
    seen_territories: set[str] = set()

    for row in rows:
        status = row["status"]
        by_status[status] = by_status.get(status, 0) + 1
        domain_value = row["domain"]
        by_domain[domain_value] = by_domain.get(domain_value, 0) + 1

        territory_name = row["territory_name"]
        if territory_name not in seen_territories and len(top_territories) < 5:
            top_territories.append(territory_name)
            seen_territories.add(territory_name)

    updated_at = max((row["updated_at"] for row in rows), default=None)
    score_version = next(
        (str(row["score_version"]) for row in rows if row.get("score_version") is not None),
        None,
    )
    return PrioritySummaryResponse(
        period=period,
        metadata=_qg_metadata(
            updated_at,
            notes="summary_derived_from_priority_drivers_mart",
            source_name="gold.mart_priority_drivers",
            config_version=score_version,
        ),
        total_items=len(rows),
        by_status=by_status,
        by_domain=by_domain,
        top_territories=top_territories,
    )


@router.get("/insights/highlights", response_model=InsightHighlightsResponse)
def get_insight_highlights(
    period: str | None = Query(default=None),
    level: str | None = Query(default="municipality"),
    domain: str | None = Query(default=None),
    severity: str | None = Query(default=None, pattern="^(info|attention|critical)$"),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),  # noqa: B008
) -> InsightHighlightsResponse:
    level_en = normalize_level(level)
    priority_rows = _fetch_priority_rows(db=db, period=period, level=level_en, domain=domain, limit=limit * 3)

    def _to_severity(status: str) -> str:
        if status == "critical":
            return "critical"
        if status == "attention":
            return "attention"
        return "info"

    insights: list[InsightHighlightItem] = []
    for row in priority_rows:
        item_severity = _to_severity(row["status"])
        if severity and item_severity != severity:
            continue
        trail = _build_explainability_trail(row)
        insights.append(
            InsightHighlightItem(
                title=f"{row['domain'].title()}: {row['territory_name']}",
                severity=item_severity,
                domain=row["domain"],
                territory_id=row["territory_id"],
                territory_name=row["territory_name"],
                explanation=_build_insight_explanation(row),
                evidence=PriorityEvidence(
                    indicator_code=row["indicator_code"],
                    reference_period=row["reference_period"],
                    source=row["source"],
                    dataset=row["dataset"],
                    updated_at=row.get("updated_at"),
                    score_version=str(row["score_version"]) if row.get("score_version") is not None else None,
                    scoring_method=str(row["scoring_method"]) if row.get("scoring_method") is not None else None,
                    domain_weight=float(row["domain_weight"]) if row.get("domain_weight") is not None else None,
                    indicator_weight=float(row["indicator_weight"]) if row.get("indicator_weight") is not None else None,
                ),
                explainability=trail,
                robustness="high" if item_severity == "critical" else "medium",
                deep_link=_build_insight_deep_link(row, item_severity),
            )
        )
        if len(insights) >= limit:
            break

    updated_at = max((row["updated_at"] for row in priority_rows), default=None)
    score_version = next(
        (str(row["score_version"]) for row in priority_rows if row.get("score_version") is not None),
        None,
    )
    return InsightHighlightsResponse(
        period=period,
        domain=domain,
        severity=severity,
        metadata=_qg_metadata(
            updated_at,
            notes="insights_v1_priority_drivers_mart",
            source_name="gold.mart_priority_drivers",
            config_version=score_version,
        ),
        items=insights,
    )


@router.post("/scenarios/simulate", response_model=ScenarioSimulateResponse)
def simulate_scenario(
    payload: ScenarioSimulateRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ScenarioSimulateResponse:
    level_en = normalize_level(payload.level) or "municipality"
    rows = _fetch_priority_rows(
        db=db,
        period=payload.period,
        level=level_en,
        domain=payload.domain,
        limit=500,
    )

    territory_rows = [
        row
        for row in rows
        if str(row["territory_id"]) == payload.territory_id and row.get("value") is not None
    ]
    if not territory_rows:
        raise HTTPException(status_code=404, detail="No indicators found for selected territory")

    target_row: dict[str, Any] | None = None
    if payload.indicator_code:
        for row in territory_rows:
            if str(row["indicator_code"]) == payload.indicator_code:
                target_row = row
                break
        if target_row is None:
            raise HTTPException(status_code=404, detail="Indicator not found for selected territory")
    else:
        target_row = territory_rows[0]

    base_value = float(target_row["value"])
    simulated_value = round(base_value * (1 + (payload.adjustment_percent / 100.0)), 6)
    delta_value = round(simulated_value - base_value, 6)

    target_indicator_code = str(target_row["indicator_code"])
    peer_candidates = [
        row
        for row in rows
        if row.get("value") is not None and str(row["indicator_code"]) == target_indicator_code
    ]
    if not peer_candidates:
        raise HTTPException(status_code=404, detail="No peers found for selected indicator")

    peers_by_territory: dict[str, dict[str, Any]] = {}
    for row in peer_candidates:
        territory_key = str(row["territory_id"])
        current = peers_by_territory.get(territory_key)
        if current is None or abs(float(row["value"])) > abs(float(current["value"])):
            peers_by_territory[territory_key] = row

    peer_rows = list(peers_by_territory.values())
    peer_rows.sort(key=lambda item: (abs(float(item["value"])), str(item["territory_name"])), reverse=True)

    base_rank = next(
        (index + 1 for index, row in enumerate(peer_rows) if str(row["territory_id"]) == payload.territory_id),
        None,
    )
    if base_rank is None:
        raise HTTPException(status_code=404, detail="Selected territory missing from peer ranking")

    simulated_rows: list[tuple[str, float]] = []
    for row in peer_rows:
        territory_key = str(row["territory_id"])
        if territory_key == payload.territory_id:
            simulated_rows.append((territory_key, simulated_value))
        else:
            simulated_rows.append((territory_key, float(row["value"])))

    simulated_rows.sort(key=lambda item: abs(item[1]), reverse=True)
    simulated_rank = next(
        (index + 1 for index, (territory_key, _value) in enumerate(simulated_rows) if territory_key == payload.territory_id),
        base_rank,
    )

    peer_count = len(peer_rows)
    base_score = _score_from_rank(base_rank, peer_count)
    simulated_score = _score_from_rank(simulated_rank, peer_count)

    status_before = _score_to_status(base_score)
    status_after = _score_to_status(simulated_score)

    rank_delta = base_rank - simulated_rank
    if status_before != status_after:
        impact = _status_impact(status_before, status_after)
    elif rank_delta > 0:
        impact = "improved"
    elif rank_delta < 0:
        impact = "worsened"
    else:
        impact = "unchanged"

    _IMPACT_LABELS = {
        "improved": "melhora",
        "worsened": "piora",
        "unchanged": "inalterado",
    }

    unit = target_row.get("unit")
    fmt_base = _format_highlight_value(base_value, unit)
    fmt_sim = _format_highlight_value(simulated_value, unit)
    fmt_delta = _format_highlight_value(delta_value, unit)
    impact_label = _IMPACT_LABELS.get(impact, impact)

    explanation = [
        f"Ajuste aplicado: {payload.adjustment_percent:.2f}% no indicador {str(target_row['indicator_name'])}.",
        f"Valor base {fmt_base} para valor simulado {fmt_sim} (delta {fmt_delta}).",
        f"Posicao no ranking do indicador: {base_rank} -> {simulated_rank} entre {peer_count} territorios.",
        f"Score de ranking estimado: {base_score:.2f} -> {simulated_score:.2f}, impacto {impact_label}.",
    ]

    return ScenarioSimulateResponse(
        territory_id=str(target_row["territory_id"]),
        territory_name=str(target_row["territory_name"]),
        territory_level=to_external_level(str(target_row["territory_level"])),
        period=payload.period,
        domain=str(target_row["domain"]),
        indicator_code=str(target_row["indicator_code"]),
        indicator_name=str(target_row["indicator_name"]),
        base_value=base_value,
        simulated_value=simulated_value,
        delta_value=delta_value,
        adjustment_percent=payload.adjustment_percent,
        base_score=base_score,
        simulated_score=simulated_score,
        peer_count=peer_count,
        base_rank=base_rank,
        simulated_rank=simulated_rank,
        rank_delta=rank_delta,
        status_before=status_before,
        status_after=status_after,
        impact=impact,
        metadata=_qg_metadata(
            max((row.get("updated_at") for row in peer_rows), default=target_row.get("updated_at")),
            notes="scenario_simulation_v1_rule_based",
            unit=target_row.get("unit"),
        ),
        explanation=explanation,
    )


@router.post("/briefs", response_model=BriefGenerateResponse)
def generate_brief(
    payload: BriefGenerateRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> BriefGenerateResponse:
    level_en = normalize_level(payload.level) or "municipality"
    rows = _fetch_priority_rows(
        db=db,
        period=payload.period,
        level=level_en,
        domain=payload.domain,
        limit=payload.limit,
    )

    if payload.territory_id:
        rows = [row for row in rows if str(row["territory_id"]) == payload.territory_id]
        if not rows:
            raise HTTPException(status_code=404, detail="No priority evidence found for selected territory")

    critical_count = sum(1 for row in rows if row["status"] == "critical")
    attention_count = sum(1 for row in rows if row["status"] == "attention")
    stable_count = sum(1 for row in rows if row["status"] == "stable")
    total_items = len(rows)

    title_scope = "Municipal"
    if payload.territory_id and rows:
        title_scope = rows[0]["territory_name"]
    elif payload.domain:
        title_scope = f"Dominio {payload.domain}"

    summary_lines: list[str] = [
        f"Foram avaliadas {total_items} evidencias no recorte selecionado.",
        f"Distribuicao de criticidade: {critical_count} criticos, {attention_count} atencao e {stable_count} estaveis.",
    ]
    if rows:
        summary_lines.append(
            f"Indicador de maior score: {rows[0]['indicator_name']} em {rows[0]['territory_name']}."
        )
    else:
        summary_lines.append("Nao ha evidencias para os filtros aplicados.")

    recommended_actions: list[str] = []
    if critical_count > 0:
        recommended_actions.append("Priorizar resposta imediata nos itens em faixa critica.")
    if attention_count > 0:
        recommended_actions.append("Monitorar semanalmente itens em atencao para evitar escalada.")
    if stable_count > 0:
        recommended_actions.append("Manter monitoramento de itens estaveis para consolidar tendencia.")
    if not recommended_actions:
        recommended_actions.append("Sem recomendacoes acionaveis para o recorte atual.")

    evidences = [
        BriefEvidenceItem(
            territory_id=str(row["territory_id"]),
            territory_name=str(row["territory_name"]),
            territory_level=to_external_level(str(row["territory_level"])),
            domain=str(row["domain"]),
            indicator_code=str(row["indicator_code"]),
            indicator_name=str(row["indicator_name"]),
            value=float(row["value"]),
            unit=row["unit"],
            score=float(row["score"]),
            status=str(row["status"]),
            source=str(row["source"]),
            dataset=str(row["dataset"]),
            reference_period=str(row["reference_period"]),
            updated_at=row.get("updated_at"),
            score_version=str(row["score_version"]) if row.get("score_version") is not None else None,
            scoring_method=str(row["scoring_method"]) if row.get("scoring_method") is not None else None,
            domain_weight=float(row["domain_weight"]) if row.get("domain_weight") is not None else None,
            indicator_weight=float(row["indicator_weight"]) if row.get("indicator_weight") is not None else None,
        )
        for row in rows
    ]

    updated_at = max((row["updated_at"] for row in rows), default=None)
    score_version = next(
        (str(row["score_version"]) for row in rows if row.get("score_version") is not None),
        None,
    )
    return BriefGenerateResponse(
        brief_id=f"brief-{uuid4().hex[:12]}",
        title=f"Brief Executivo - {title_scope}",
        generated_at=datetime.now(UTC),
        period=payload.period,
        level=to_external_level(level_en),
        territory_id=payload.territory_id,
        domain=payload.domain,
        summary_lines=summary_lines,
        recommended_actions=recommended_actions,
        evidences=evidences,
        metadata=_qg_metadata(updated_at, notes="brief_v1_rule_based", config_version=score_version),
    )


@router.get("/territory/{territory_id}/profile", response_model=TerritoryProfileResponse)
def get_territory_profile(
    territory_id: str,
    period: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=300),
    db: Session = Depends(get_db),  # noqa: B008
) -> TerritoryProfileResponse:
    territory = _get_territory_context(db, territory_id)
    if territory is None:
        raise HTTPException(status_code=404, detail="Territory not found")

    territory_level = str(territory["territory_level"])
    rows = _fetch_latest_indicator_rows(db=db, territory_id=territory_id, period=period)[:limit]
    indicator_score_rows = _fetch_territory_indicator_scores(
        db=db,
        territory_id=territory_id,
        period=period,
        level=territory_level,
    )
    score_by_indicator: dict[str, dict[str, Any]] = {
        str(row["indicator_code"]): row for row in indicator_score_rows
    }

    domains_map: dict[str, list[TerritoryProfileIndicator]] = {}
    domain_scores: dict[str, list[float]] = {}
    for row in rows:
        domain = str(row["domain"])
        score_row = score_by_indicator.get(str(row["indicator_code"]))
        indicator_status = str(score_row["status"]) if score_row else "stable"
        if score_row:
            domain_scores.setdefault(domain, []).append(float(score_row["score"]))
        domains_map.setdefault(domain, []).append(
            TerritoryProfileIndicator(
                indicator_code=row["indicator_code"],
                indicator_name=row["indicator_name"],
                value=float(row["value"]),
                unit=row["unit"],
                reference_period=row["reference_period"],
                status=indicator_status,
            )
        )

    domains: list[TerritoryProfileDomain] = []
    computed_domain_scores: list[float] = []
    for domain in sorted(domains_map.keys()):
        indicators = domains_map[domain]
        domain_score_values = domain_scores.get(domain, [])
        domain_score = round(sum(domain_score_values) / len(domain_score_values), 2) if domain_score_values else None
        domain_status = _score_to_status(domain_score) if domain_score is not None else "stable"
        if domain_score is not None:
            computed_domain_scores.append(domain_score)
        domains.append(
            TerritoryProfileDomain(
                domain=domain,
                status=domain_status,
                score=domain_score,
                indicators_count=len(indicators),
                indicators=indicators,
            )
        )

    highlights: list[str] = []
    for row in sorted(rows, key=lambda item: abs(float(item["value"])), reverse=True)[:3]:
        formatted_value = _format_highlight_value(float(row["value"]), row.get("unit"))
        highlights.append(
            f"Destaque: {row['indicator_name']} em {row['reference_period']}: {formatted_value}."
        )
    if not highlights:
        highlights = ["Sem indicadores disponiveis para os filtros aplicados."]

    overall_score = None
    if computed_domain_scores:
        overall_score = round(sum(computed_domain_scores) / len(computed_domain_scores), 2)
    overall_status = _score_to_status(overall_score) if overall_score is not None else "stable"

    overall_trend = "flat"
    previous_period = _previous_reference_period(period)
    if previous_period:
        previous_indicator_score_rows = _fetch_territory_indicator_scores(
            db=db,
            territory_id=territory_id,
            period=previous_period,
            level=territory_level,
        )
        previous_score_by_indicator = {
            str(row["indicator_code"]): float(row["score"]) for row in previous_indicator_score_rows
        }
        shared_codes = set(score_by_indicator.keys()) & set(previous_score_by_indicator.keys())
        if shared_codes:
            current_avg = sum(float(score_by_indicator[code]["score"]) for code in shared_codes) / len(shared_codes)
            previous_avg = sum(previous_score_by_indicator[code] for code in shared_codes) / len(shared_codes)
            delta = current_avg - previous_avg
            if delta >= 2:
                overall_trend = "up"
            elif delta <= -2:
                overall_trend = "down"

    updated_at = max((row["updated_at"] for row in rows), default=None)
    return TerritoryProfileResponse(
        territory_id=territory["territory_id"],
        territory_name=territory["territory_name"],
        territory_level=to_external_level(territory_level),
        period=period,
        overall_score=overall_score,
        overall_status=overall_status,
        overall_trend=overall_trend,
        metadata=_qg_metadata(updated_at, notes="territory_profile_latest_indicators_v1"),
        highlights=highlights,
        domains=domains,
    )


@router.get("/territory/{territory_id}/compare", response_model=TerritoryCompareResponse)
def get_territory_compare(
    territory_id: str,
    with_id: str = Query(...),
    period: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=300),
    db: Session = Depends(get_db),  # noqa: B008
) -> TerritoryCompareResponse:
    base_territory = _get_territory_context(db, territory_id)
    if base_territory is None:
        raise HTTPException(status_code=404, detail="Base territory not found")

    compare_territory = _get_territory_context(db, with_id)
    if compare_territory is None:
        raise HTTPException(status_code=404, detail="Comparison territory not found")

    base_rows = _fetch_latest_indicator_rows(db=db, territory_id=territory_id, period=period)
    compare_rows = _fetch_latest_indicator_rows(db=db, territory_id=with_id, period=period)

    base_by_code = {str(row["indicator_code"]): row for row in base_rows}
    compare_by_code = {str(row["indicator_code"]): row for row in compare_rows}
    shared_codes = set(base_by_code.keys()) & set(compare_by_code.keys())

    items: list[TerritoryCompareItem] = []
    for indicator_code in shared_codes:
        base_row = base_by_code[indicator_code]
        compare_row = compare_by_code[indicator_code]

        base_value = float(base_row["value"])
        compare_value = float(compare_row["value"])
        delta = base_value - compare_value
        if delta > 0:
            direction = "up"
        elif delta < 0:
            direction = "down"
        else:
            direction = "flat"

        delta_percent = None
        if compare_value != 0:
            delta_percent = round((delta / abs(compare_value)) * 100, 6)

        items.append(
            TerritoryCompareItem(
                domain=base_row["domain"],
                indicator_code=indicator_code,
                indicator_name=base_row["indicator_name"],
                unit=base_row["unit"],
                reference_period=base_row["reference_period"],
                base_value=base_value,
                compare_value=compare_value,
                delta=round(delta, 6),
                delta_percent=delta_percent,
                direction=direction,
            )
        )

    items.sort(key=lambda item: abs(item.delta), reverse=True)
    items = items[:limit]
    updated_at = max(
        [row["updated_at"] for row in base_rows] + [row["updated_at"] for row in compare_rows],
        default=None,
    )

    return TerritoryCompareResponse(
        territory_id=base_territory["territory_id"],
        territory_name=base_territory["territory_name"],
        compare_with_id=compare_territory["territory_id"],
        compare_with_name=compare_territory["territory_name"],
        period=period,
        metadata=_qg_metadata(updated_at, notes="territory_compare_latest_indicators_v1"),
        items=items,
    )


@router.get("/territory/{territory_id}/peers", response_model=TerritoryPeersResponse)
def get_territory_peers(
    territory_id: str,
    period: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),  # noqa: B008
) -> TerritoryPeersResponse:
    territory = _get_territory_context(db, territory_id)
    if territory is None:
        raise HTTPException(status_code=404, detail="Territory not found")

    territory_level = str(territory["territory_level"])
    target_rows = _fetch_territory_indicator_scores(
        db=db,
        territory_id=territory_id,
        period=period,
        level=territory_level,
    )
    if not target_rows:
        raise HTTPException(status_code=404, detail="No indicators found for selected territory")

    all_rows = _fetch_territory_indicator_scores(
        db=db,
        territory_id=None,
        period=period,
        level=territory_level,
    )

    target_scores = {str(row["indicator_code"]): float(row["score"]) for row in target_rows}
    rows_by_territory: dict[str, dict[str, Any]] = {}
    for row in all_rows:
        candidate_territory_id = str(row["territory_id"])
        if candidate_territory_id == territory_id:
            continue
        bucket = rows_by_territory.setdefault(
            candidate_territory_id,
            {
                "territory_id": candidate_territory_id,
                "territory_name": str(row["territory_name"]),
                "territory_level": str(row["territory_level"]),
                "scores": {},
                "updated_at_rows": [],
            },
        )
        bucket["scores"][str(row["indicator_code"])] = float(row["score"])
        if row.get("updated_at") is not None:
            bucket["updated_at_rows"].append(row["updated_at"])

    peer_items: list[TerritoryPeerItem] = []
    updated_at_values: list[datetime] = []
    for candidate in rows_by_territory.values():
        candidate_scores = candidate["scores"]
        shared_codes = sorted(set(target_scores.keys()) & set(candidate_scores.keys()))
        if not shared_codes:
            continue

        mean_abs_error = sum(abs(target_scores[code] - candidate_scores[code]) for code in shared_codes) / len(shared_codes)
        similarity_score = round(max(0.0, 100.0 - mean_abs_error), 2)
        avg_score = round(sum(candidate_scores[code] for code in shared_codes) / len(shared_codes), 2)

        peer_items.append(
            TerritoryPeerItem(
                territory_id=candidate["territory_id"],
                territory_name=candidate["territory_name"],
                territory_level=to_external_level(candidate["territory_level"]),
                similarity_score=similarity_score,
                shared_indicators=len(shared_codes),
                avg_score=avg_score,
                status=_score_to_status(avg_score),
            )
        )
        updated_at_values.extend(candidate["updated_at_rows"])

    peer_items.sort(
        key=lambda item: (
            item.shared_indicators,
            item.similarity_score,
            item.territory_name,
        ),
        reverse=True,
    )
    peer_items = peer_items[:limit]

    updated_at = max(updated_at_values, default=None)
    return TerritoryPeersResponse(
        territory_id=territory["territory_id"],
        territory_name=territory["territory_name"],
        territory_level=to_external_level(territory_level),
        period=period,
        metadata=_qg_metadata(updated_at, notes="territory_peers_v1_similarity_rule_based"),
        items=peer_items,
    )


@router.get("/electorate/summary", response_model=ElectorateSummaryResponse)
def get_electorate_summary(
    level: str = Query(default="municipality"),
    year: int | None = Query(default=None, ge=1900, le=2100),
    db: Session = Depends(get_db),  # noqa: B008
) -> ElectorateSummaryResponse:
    level_en = normalize_level(level) or "municipality"
    effective_year, electorate_storage_year, electorate_year_note = _resolve_electorate_year_binding(
        db,
        level=level_en,
        requested_year=year,
    )

    if effective_year is None or electorate_storage_year is None:
        return ElectorateSummaryResponse(
            level=to_external_level(level_en),
            year=None,
            metadata=QgMetadata(
                source_name="silver.fact_electorate",
                updated_at=None,
                coverage_note="territorial_aggregated",
                unit="voters",
                notes="no_data_for_selected_filters",
                source_classification="oficial",
                config_version=load_strategic_engine_config().version,
            ),
            total_voters=0,
            turnout=None,
            turnout_rate=None,
            abstention_rate=None,
            blank_rate=None,
            null_rate=None,
            by_sex=[],
            by_age=[],
            by_education=[],
        )

    total_voters = int(
        db.execute(
            text(
                """
                SELECT COALESCE(SUM(fe.voters), 0)::bigint AS total_voters
                FROM silver.fact_electorate fe
                JOIN silver.dim_territory dt ON dt.territory_id = fe.territory_id
                WHERE dt.level::text = :level
                  AND fe.reference_year = :year
                """
            ),
            {"level": level_en, "year": electorate_storage_year},
        ).scalar_one()
    )

    by_sex = _fetch_electorate_breakdown(db, level=level_en, year=electorate_storage_year, breakdown_kind="sex")
    by_age = _fetch_electorate_breakdown(db, level=level_en, year=electorate_storage_year, breakdown_kind="age")
    by_education = _fetch_electorate_breakdown(db, level=level_en, year=electorate_storage_year, breakdown_kind="education")

    election_year = _resolve_available_year(
        db,
        level=level_en,
        requested_year=effective_year,
        table_kind="election",
    )
    election_metrics = (
        _fetch_election_metrics(db, level=level_en, year=election_year) if election_year is not None else {}
    )

    turnout = election_metrics.get("turnout")
    abstention = election_metrics.get("abstention")
    votes_total = election_metrics.get("votes_total")
    votes_blank = election_metrics.get("votes_blank")
    votes_null = election_metrics.get("votes_null")

    turnout_rate = None
    abstention_rate = None
    if turnout is not None and abstention is not None and (turnout + abstention) > 0:
        turnout_rate = round((turnout / (turnout + abstention)) * 100, 6)
        abstention_rate = round((abstention / (turnout + abstention)) * 100, 6)

    blank_rate = None
    null_rate = None
    if votes_total is not None and votes_total > 0:
        if votes_blank is not None:
            blank_rate = round((votes_blank / votes_total) * 100, 6)
        if votes_null is not None:
            null_rate = round((votes_null / votes_total) * 100, 6)

    return ElectorateSummaryResponse(
        level=to_external_level(level_en),
        year=effective_year,
        metadata=QgMetadata(
            source_name="silver.fact_electorate + silver.fact_election_result",
            updated_at=None,
            coverage_note="territorial_aggregated",
            unit="voters",
            notes=electorate_year_note or "electorate_summary_v1",
            source_classification="oficial",
            config_version=load_strategic_engine_config().version,
        ),
        total_voters=total_voters,
        turnout=turnout,
        turnout_rate=turnout_rate,
        abstention_rate=abstention_rate,
        blank_rate=blank_rate,
        null_rate=null_rate,
        by_sex=by_sex,
        by_age=by_age,
        by_education=by_education,
    )


@router.get("/electorate/map", response_model=ElectorateMapResponse)
def get_electorate_map(
    level: str = Query(default="municipality"),
    metric: str = Query(default="voters", pattern="^(voters|turnout|abstention_rate|blank_rate|null_rate)$"),
    year: int | None = Query(default=None, ge=1900, le=2100),
    include_geometry: bool = Query(default=True),
    limit: int = Query(default=1000, ge=1, le=5000),
    db: Session = Depends(get_db),  # noqa: B008
) -> ElectorateMapResponse:
    level_en = normalize_level(level) or "municipality"
    geometry_select = "ST_AsGeoJSON(dt.geometry)::jsonb AS geometry" if include_geometry else "NULL::jsonb AS geometry"

    if metric == "voters":
        effective_year, electorate_storage_year, electorate_year_note = _resolve_electorate_year_binding(
            db,
            level=level_en,
            requested_year=year,
        )
        if effective_year is None or electorate_storage_year is None:
            return ElectorateMapResponse(
                level=to_external_level(level_en),
                metric=metric,
                year=None,
                metadata=QgMetadata(
                    source_name="silver.fact_electorate",
                    updated_at=None,
                    coverage_note="territorial_aggregated",
                    unit="voters",
                    notes="no_data_for_selected_filters",
                    source_classification="oficial",
                    config_version=load_strategic_engine_config().version,
                ),
                items=[],
            )

        rows = db.execute(
            text(
                f"""
                SELECT
                    dt.territory_id::text AS territory_id,
                    dt.name AS territory_name,
                    dt.level::text AS territory_level,
                    SUM(fe.voters)::double precision AS value,
                    {geometry_select}
                FROM silver.fact_electorate fe
                JOIN silver.dim_territory dt ON dt.territory_id = fe.territory_id
                WHERE dt.level::text = :level
                  AND fe.reference_year = :year
                GROUP BY dt.territory_id, dt.name, dt.level, dt.geometry
                ORDER BY dt.name ASC
                LIMIT :limit
                """
            ),
            {"level": level_en, "year": electorate_storage_year, "limit": limit},
        ).mappings().all()

        items = [
            ElectorateMapItem(
                territory_id=row["territory_id"],
                territory_name=row["territory_name"],
                territory_level=to_external_level(row["territory_level"]),
                metric=metric,
                value=float(row["value"]) if row["value"] is not None else None,
                year=effective_year,
                geometry=row["geometry"],
            )
            for row in rows
        ]
        return ElectorateMapResponse(
            level=to_external_level(level_en),
            metric=metric,
            year=effective_year,
            metadata=QgMetadata(
                source_name="silver.fact_electorate",
                updated_at=None,
                coverage_note="territorial_aggregated",
                unit="voters",
                notes=electorate_year_note or "electorate_map_v1",
                source_classification="oficial",
                config_version=load_strategic_engine_config().version,
            ),
            items=items,
        )

    effective_year = _resolve_available_year(
        db,
        level=level_en,
        requested_year=year,
        table_kind="election",
    )
    if effective_year is None:
        return ElectorateMapResponse(
            level=to_external_level(level_en),
            metric=metric,
            year=None,
            metadata=QgMetadata(
                source_name="silver.fact_election_result",
                updated_at=None,
                coverage_note="territorial_aggregated",
                unit="%",
                notes="no_data_for_selected_filters",
                source_classification="oficial",
                config_version=load_strategic_engine_config().version,
            ),
            items=[],
        )

    rows = db.execute(
        text(
            f"""
            WITH grouped AS (
                SELECT
                    dt.territory_id::text AS territory_id,
                    dt.name AS territory_name,
                    dt.level::text AS territory_level,
                    SUM(CASE WHEN fr.metric = 'turnout' THEN fr.value ELSE 0 END)::double precision AS turnout,
                    SUM(CASE WHEN fr.metric = 'abstention' THEN fr.value ELSE 0 END)::double precision AS abstention,
                    SUM(CASE WHEN fr.metric = 'votes_blank' THEN fr.value ELSE 0 END)::double precision AS votes_blank,
                    SUM(CASE WHEN fr.metric = 'votes_null' THEN fr.value ELSE 0 END)::double precision AS votes_null,
                    SUM(CASE WHEN fr.metric = 'votes_total' THEN fr.value ELSE 0 END)::double precision AS votes_total,
                    {geometry_select}
                FROM silver.fact_election_result fr
                JOIN silver.dim_territory dt ON dt.territory_id = fr.territory_id
                WHERE dt.level::text = :level
                  AND fr.election_year = :year
                GROUP BY dt.territory_id, dt.name, dt.level, dt.geometry
            )
            SELECT
                territory_id,
                territory_name,
                territory_level,
                CASE
                    WHEN :metric = 'turnout' THEN turnout
                    WHEN :metric = 'abstention_rate' THEN (abstention / NULLIF(turnout + abstention, 0)) * 100
                    WHEN :metric = 'blank_rate' THEN (votes_blank / NULLIF(votes_total, 0)) * 100
                    WHEN :metric = 'null_rate' THEN (votes_null / NULLIF(votes_total, 0)) * 100
                    ELSE NULL
                END::double precision AS value,
                geometry
            FROM grouped
            ORDER BY territory_name ASC
            LIMIT :limit
            """
        ),
        {"level": level_en, "year": effective_year, "metric": metric, "limit": limit},
    ).mappings().all()

    items = [
        ElectorateMapItem(
            territory_id=row["territory_id"],
            territory_name=row["territory_name"],
            territory_level=to_external_level(row["territory_level"]),
            metric=metric,
            value=float(row["value"]) if row["value"] is not None else None,
            year=effective_year,
            geometry=row["geometry"],
        )
        for row in rows
    ]
    return ElectorateMapResponse(
        level=to_external_level(level_en),
        metric=metric,
        year=effective_year,
        metadata=QgMetadata(
            source_name="silver.fact_election_result",
            updated_at=None,
            coverage_note="territorial_aggregated",
            unit="%" if metric.endswith("_rate") else "voters",
            notes="electorate_map_v1",
            source_classification="oficial",
            config_version=load_strategic_engine_config().version,
        ),
        items=items,
    )
