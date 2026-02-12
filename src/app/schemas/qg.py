from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class QgMetadata(BaseModel):
    source_name: str
    updated_at: datetime | None = None
    coverage_note: str
    unit: str | None = None
    notes: str | None = None


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


class InsightHighlightItem(BaseModel):
    title: str
    severity: str
    domain: str
    territory_id: str
    territory_name: str
    explanation: list[str]
    evidence: PriorityEvidence
    robustness: str


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
