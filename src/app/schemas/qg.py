from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class QgMetadata(BaseModel):
    source_name: str
    updated_at: datetime | None = None
    coverage_note: str
    unit: str | None = None
    notes: str | None = None
    source_classification: str | None = None
    config_version: str | None = None


class ExplainabilityCoverage(BaseModel):
    covered_territories: int
    total_territories: int
    coverage_pct: float


class ExplainabilityTrail(BaseModel):
    trail_id: str
    score_version: str | None = None
    scoring_method: str | None = None
    driver_rank: int | None = None
    driver_total: int | None = None
    weighted_magnitude: float | None = None
    critical_threshold: float | None = None
    attention_threshold: float | None = None
    coverage: ExplainabilityCoverage | None = None


class KpiOverviewItem(BaseModel):
    domain: str
    source: str | None = None
    dataset: str | None = None
    indicator_code: str
    indicator_name: str
    value: float
    unit: str | None = None
    delta: float | None = None
    status: str
    territory_level: str


class KpiOverviewResponse(BaseModel):
    period: str | None
    metadata: QgMetadata
    items: list[KpiOverviewItem]


class PriorityEvidence(BaseModel):
    indicator_code: str
    reference_period: str
    source: str
    dataset: str
    updated_at: datetime | None = None
    score_version: str | None = None
    scoring_method: str | None = None
    domain_weight: float | None = None
    indicator_weight: float | None = None


class PriorityItem(BaseModel):
    territory_id: str
    territory_name: str
    territory_level: str
    domain: str
    indicator_code: str
    indicator_name: str
    value: float
    unit: str | None = None
    score: float
    trend: str
    status: str
    rationale: list[str]
    evidence: PriorityEvidence
    explainability: ExplainabilityTrail


class PriorityListResponse(BaseModel):
    period: str | None
    level: str | None
    domain: str | None
    metadata: QgMetadata
    items: list[PriorityItem]


class PrioritySummaryResponse(BaseModel):
    period: str | None
    metadata: QgMetadata
    total_items: int
    by_status: dict[str, int]
    by_domain: dict[str, int]
    top_territories: list[str]


class MobilityAccessItem(BaseModel):
    reference_period: str
    territory_id: str
    territory_name: str
    territory_level: str
    municipality_ibge_code: str | None = None
    road_segments_count: int
    road_length_km: float
    transport_stops_count: int
    mobility_pois_count: int
    fleet_total_effective: float | None = None
    population_effective: float | None = None
    vehicles_per_1k_pop: float | None = None
    transport_stops_per_10k_pop: float | None = None
    road_km_per_10k_pop: float | None = None
    mobility_pois_per_10k_pop: float | None = None
    mobility_access_score: float
    mobility_access_deficit_score: float
    priority_status: str
    uses_proxy_allocation: bool
    allocation_method: str


class MobilityAccessResponse(BaseModel):
    period: str | None
    level: str | None
    metadata: QgMetadata
    items: list[MobilityAccessItem]


class EnvironmentRiskItem(BaseModel):
    reference_period: str
    territory_id: str
    territory_name: str
    territory_level: str
    municipality_ibge_code: str | None = None
    hazard_score: float
    exposure_score: float
    environment_risk_score: float
    risk_percentile: float
    risk_priority_rank: int
    priority_status: str
    area_km2: float | None = None
    road_km: float | None = None
    pois_count: int
    transport_stops_count: int
    road_density_km_per_km2: float | None = None
    pois_per_km2: float | None = None
    transport_stops_per_km2: float | None = None
    population_effective: float | None = None
    exposed_population_per_km2: float | None = None
    uses_proxy_allocation: bool
    allocation_method: str


class EnvironmentRiskResponse(BaseModel):
    period: str | None
    level: str | None
    metadata: QgMetadata
    items: list[EnvironmentRiskItem]


class InsightHighlightItem(BaseModel):
    title: str
    severity: str
    domain: str
    territory_id: str
    territory_name: str
    explanation: list[str]
    evidence: PriorityEvidence
    explainability: ExplainabilityTrail
    robustness: str
    deep_link: str | None = None


class InsightHighlightsResponse(BaseModel):
    period: str | None
    domain: str | None
    severity: str | None
    metadata: QgMetadata
    items: list[InsightHighlightItem]


class TerritoryProfileIndicator(BaseModel):
    indicator_code: str
    indicator_name: str
    value: float
    unit: str | None = None
    reference_period: str
    status: str


class TerritoryProfileDomain(BaseModel):
    domain: str
    status: str
    score: float | None = None
    indicators_count: int
    indicators: list[TerritoryProfileIndicator]


class TerritoryProfileResponse(BaseModel):
    territory_id: str
    territory_name: str
    territory_level: str
    period: str | None
    overall_score: float | None = None
    overall_status: str
    overall_trend: str = "flat"
    metadata: QgMetadata
    highlights: list[str]
    domains: list[TerritoryProfileDomain]


class TerritoryCompareItem(BaseModel):
    domain: str
    indicator_code: str
    indicator_name: str
    unit: str | None = None
    reference_period: str
    base_value: float
    compare_value: float
    delta: float
    delta_percent: float | None = None
    direction: str


class TerritoryCompareResponse(BaseModel):
    territory_id: str
    territory_name: str
    compare_with_id: str
    compare_with_name: str
    period: str | None
    metadata: QgMetadata
    items: list[TerritoryCompareItem]


class TerritoryPeerItem(BaseModel):
    territory_id: str
    territory_name: str
    territory_level: str
    similarity_score: float
    shared_indicators: int
    avg_score: float | None = None
    status: str


class TerritoryPeersResponse(BaseModel):
    territory_id: str
    territory_name: str
    territory_level: str
    period: str | None
    metadata: QgMetadata
    items: list[TerritoryPeerItem]


class ElectorateBreakdownItem(BaseModel):
    label: str
    voters: int
    share_percent: float


class ElectorateSummaryResponse(BaseModel):
    level: str
    year: int | None
    metadata: QgMetadata
    total_voters: int
    turnout: float | None = None
    turnout_rate: float | None = None
    abstention_rate: float | None = None
    blank_rate: float | None = None
    null_rate: float | None = None
    by_sex: list[ElectorateBreakdownItem]
    by_age: list[ElectorateBreakdownItem]
    by_education: list[ElectorateBreakdownItem]


class ElectorateMapItem(BaseModel):
    territory_id: str
    territory_name: str
    territory_level: str
    metric: str
    value: float | None = None
    year: int | None = None
    geometry: dict | None = None
    polling_place_name: str | None = None
    polling_place_code: str | None = None
    section_count: int | None = None
    sections: list[str] | None = None


class ElectorateMapResponse(BaseModel):
    level: str
    metric: str
    year: int | None
    metadata: QgMetadata
    items: list[ElectorateMapItem]


class ScenarioSimulateRequest(BaseModel):
    territory_id: str
    period: str | None = None
    level: str | None = "municipality"
    domain: str | None = None
    indicator_code: str | None = None
    adjustment_percent: float = Field(ge=-95, le=300)


class ScenarioSimulateResponse(BaseModel):
    territory_id: str
    territory_name: str
    territory_level: str
    period: str | None
    domain: str
    indicator_code: str
    indicator_name: str
    base_value: float
    simulated_value: float
    delta_value: float
    adjustment_percent: float
    base_score: float
    simulated_score: float
    peer_count: int
    base_rank: int
    simulated_rank: int
    rank_delta: int
    status_before: str
    status_after: str
    impact: str
    metadata: QgMetadata
    explanation: list[str]


class BriefGenerateRequest(BaseModel):
    period: str | None = None
    level: str | None = "municipality"
    territory_id: str | None = None
    domain: str | None = None
    limit: int = Field(default=20, ge=1, le=200)


class BriefEvidenceItem(BaseModel):
    territory_id: str
    territory_name: str
    territory_level: str
    domain: str
    indicator_code: str
    indicator_name: str
    value: float
    unit: str | None = None
    score: float
    status: str
    source: str
    dataset: str
    reference_period: str
    updated_at: datetime | None = None
    score_version: str | None = None
    scoring_method: str | None = None
    domain_weight: float | None = None
    indicator_weight: float | None = None


class BriefGenerateResponse(BaseModel):
    brief_id: str
    title: str
    generated_at: datetime
    period: str | None
    level: str | None
    territory_id: str | None
    domain: str | None
    summary_lines: list[str]
    recommended_actions: list[str]
    evidences: list[BriefEvidenceItem]
    metadata: QgMetadata
