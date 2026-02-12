from __future__ import annotations

from datetime import UTC
from datetime import datetime
from uuid import uuid4
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.territory_levels import normalize_level, to_external_level
from app.schemas.qg import (
    BriefEvidenceItem,
    BriefGenerateRequest,
    BriefGenerateResponse,
    ElectorateBreakdownItem,
    ElectorateMapItem,
    ElectorateMapResponse,
    ElectorateSummaryResponse,
    InsightHighlightItem,
    InsightHighlightsResponse,
    KpiOverviewItem,
    KpiOverviewResponse,
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


def _qg_metadata(updated_at: datetime | None, notes: str | None = None, unit: str | None = None) -> QgMetadata:
    return QgMetadata(
        source_name="silver.fact_indicator",
        updated_at=updated_at,
        coverage_note="territorial_aggregated",
        unit=unit,
        notes=notes,
    )


def _fetch_priority_rows(
    db: Session,
    period: str | None,
    level: str | None,
    domain: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    query = text(
        f"""
        WITH base AS (
            SELECT
                dt.territory_id::text AS territory_id,
                dt.name AS territory_name,
                dt.level::text AS territory_level,
                {_DOMAIN_CASE_SQL} AS domain,
                fi.indicator_code,
                fi.indicator_name,
                fi.value::double precision AS value,
                fi.unit,
                fi.reference_period,
                fi.source,
                fi.dataset,
                fi.updated_at
            FROM silver.fact_indicator fi
            JOIN silver.dim_territory dt ON dt.territory_id = fi.territory_id
            WHERE (CAST(:period AS TEXT) IS NULL OR fi.reference_period = CAST(:period AS TEXT))
              AND (CAST(:level AS TEXT) IS NULL OR dt.level::text = CAST(:level AS TEXT))
        ),
        filtered AS (
            SELECT *
            FROM base
            WHERE (CAST(:domain AS TEXT) IS NULL OR domain = CAST(:domain AS TEXT))
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (ORDER BY ABS(value) DESC, territory_name ASC, indicator_code ASC) AS row_num,
                COUNT(*) OVER () AS total_rows
            FROM filtered
        ),
        scored AS (
            SELECT
                *,
                CASE
                    WHEN total_rows <= 1 THEN 100.0
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
            indicator_name,
            value,
            unit,
            reference_period,
            source,
            dataset,
            updated_at,
            score,
            CASE
                WHEN score >= 80 THEN 'critical'
                WHEN score >= 50 THEN 'attention'
                ELSE 'stable'
            END AS status
        FROM scored
        ORDER BY row_num
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
    if score >= 80:
        return "critical"
    if score >= 50:
        return "attention"
    return "stable"


def _score_from_rank(rank: int, total_items: int) -> float:
    if total_items <= 1:
        return 100.0
    return round((1 - ((rank - 1) / (total_items - 1))) * 100, 2)


def _status_impact(before: str, after: str) -> str:
    weights = {"stable": 0, "attention": 1, "critical": 2}
    before_weight = weights.get(before, 0)
    after_weight = weights.get(after, 0)
    if after_weight > before_weight:
        return "worsened"
    if after_weight < before_weight:
        return "improved"
    return "unchanged"


def _previous_reference_period(period: str | None) -> str | None:
    if period is None:
        return None
    normalized = period.strip()
    if normalized.isdigit() and len(normalized) == 4:
        return str(int(normalized) - 1)
    return None


def _fetch_territory_indicator_scores(
    db: Session,
    *,
    territory_id: str | None,
    period: str | None,
    level: str,
) -> list[dict[str, Any]]:
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
                        WHEN total_rows <= 1 THEN 100.0
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
                    WHEN score >= 80 THEN 'critical'
                    WHEN score >= 50 THEN 'attention'
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

    items = []
    for row in rows:
        rationale = [
            f"Indicador {row['indicator_code']} com valor {row['value']:.2f}.",
            f"Dominio {row['domain']} em {row['territory_name']}.",
        ]
        if row["status"] == "critical":
            rationale.append("Criticidade alta dentro do recorte atual.")
        elif row["status"] == "attention":
            rationale.append("Indicador em faixa de atencao no recorte atual.")
        else:
            rationale.append("Indicador em faixa estavel no recorte atual.")

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
                trend="stable",
                status=row["status"],
                rationale=rationale,
                evidence=PriorityEvidence(
                    indicator_code=row["indicator_code"],
                    reference_period=row["reference_period"],
                    source=row["source"],
                    dataset=row["dataset"],
                ),
            )
        )

    updated_at = max((row["updated_at"] for row in rows), default=None)
    return PriorityListResponse(
        period=period,
        level=to_external_level(level_en) if level_en else None,
        domain=domain,
        metadata=_qg_metadata(updated_at, notes="ranking_derived_from_fact_indicator"),
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
    return PrioritySummaryResponse(
        period=period,
        metadata=_qg_metadata(updated_at, notes="summary_derived_from_priority_list"),
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
        insights.append(
            InsightHighlightItem(
                title=f"{row['domain'].title()}: {row['territory_name']}",
                severity=item_severity,
                domain=row["domain"],
                territory_id=row["territory_id"],
                territory_name=row["territory_name"],
                explanation=[
                    f"O indicador {row['indicator_code']} apresentou valor {row['value']:.2f}.",
                    f"Score de priorizacao calculado em {row['score']:.2f}.",
                    "Insight inicial baseado em ranking do recorte atual.",
                ],
                evidence=PriorityEvidence(
                    indicator_code=row["indicator_code"],
                    reference_period=row["reference_period"],
                    source=row["source"],
                    dataset=row["dataset"],
                ),
                robustness="high" if item_severity == "critical" else "medium",
            )
        )
        if len(insights) >= limit:
            break

    updated_at = max((row["updated_at"] for row in priority_rows), default=None)
    return InsightHighlightsResponse(
        period=period,
        domain=domain,
        severity=severity,
        metadata=_qg_metadata(updated_at, notes="insights_v1_rule_based"),
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

    explanation = [
        f"Ajuste aplicado: {payload.adjustment_percent:.2f}% no indicador {target_indicator_code}.",
        f"Valor base {base_value:.2f} para valor simulado {simulated_value:.2f} (delta {delta_value:.2f}).",
        f"Posicao no ranking do indicador: {base_rank} -> {simulated_rank} entre {peer_count} territorios.",
        f"Score de ranking estimado: {base_score:.2f} -> {simulated_score:.2f}, impacto {impact}.",
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
            f"Indicador de maior score: {rows[0]['indicator_name']} ({rows[0]['indicator_code']}) em {rows[0]['territory_name']}."
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
        )
        for row in rows
    ]

    updated_at = max((row["updated_at"] for row in rows), default=None)
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
        metadata=_qg_metadata(updated_at, notes="brief_v1_rule_based"),
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
        highlights.append(
            f"{row['indicator_name']} ({row['indicator_code']}) em {row['reference_period']}: {float(row['value']):.2f}."
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
    effective_year = _resolve_available_year(
        db,
        level=level_en,
        requested_year=year,
        table_kind="electorate",
    )

    if effective_year is None:
        return ElectorateSummaryResponse(
            level=to_external_level(level_en),
            year=None,
            metadata=QgMetadata(
                source_name="silver.fact_electorate",
                updated_at=None,
                coverage_note="territorial_aggregated",
                unit="voters",
                notes="no_data_for_selected_filters",
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
            {"level": level_en, "year": effective_year},
        ).scalar_one()
    )

    by_sex = _fetch_electorate_breakdown(db, level=level_en, year=effective_year, breakdown_kind="sex")
    by_age = _fetch_electorate_breakdown(db, level=level_en, year=effective_year, breakdown_kind="age")
    by_education = _fetch_electorate_breakdown(db, level=level_en, year=effective_year, breakdown_kind="education")

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
            notes="electorate_summary_v1",
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
        effective_year = _resolve_available_year(
            db,
            level=level_en,
            requested_year=year,
            table_kind="electorate",
        )
        if effective_year is None:
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
            {"level": level_en, "year": effective_year, "limit": limit},
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
                notes="electorate_map_v1",
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
        ),
        items=items,
    )
