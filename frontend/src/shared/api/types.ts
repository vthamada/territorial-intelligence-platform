export type ApiErrorPayload = {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
    request_id?: string;
  };
};

export type PaginatedResponse<T> = {
  page: number;
  page_size: number;
  total: number;
  items: T[];
};

export type PipelineRun = {
  run_id: string;
  job_name: string;
  source: string;
  dataset: string;
  wave: string;
  reference_period: string;
  started_at_utc: string;
  finished_at_utc: string | null;
  duration_seconds: number | null;
  status: string;
  rows_extracted: number;
  rows_loaded: number;
  warnings_count: number;
  errors_count: number;
};

export type PipelineCheck = {
  check_id: number;
  run_id: string;
  job_name: string;
  source: string;
  dataset: string;
  wave: string;
  reference_period: string;
  check_name: string;
  status: string;
  details: string;
  observed_value: number | null;
  threshold_value: number | null;
  created_at_utc: string;
};

export type ConnectorRegistryItem = {
  connector_name: string;
  source: string;
  wave: string;
  status: string;
  notes: string | null;
  updated_at_utc: string;
};

export type FrontendEventItem = {
  event_id: number;
  category: "frontend_error" | "web_vital" | "performance" | "lifecycle" | "api_request" | string;
  name: string;
  severity: "info" | "warn" | "error" | string;
  attributes: Record<string, unknown> | null;
  event_timestamp_utc: string;
  received_at_utc: string;
  request_id: string | null;
  user_agent: string | null;
};

export type OpsSummaryResponse = {
  runs: {
    total: number;
    by_status: Record<string, number>;
    by_wave: Record<string, number>;
    latest_started_at_utc: string | null;
  };
  checks: {
    total: number;
    by_status: Record<string, number>;
    latest_created_at_utc: string | null;
  };
  connectors: {
    total: number;
    by_status: Record<string, number>;
    by_wave: Record<string, number>;
    latest_updated_at_utc: string | null;
  };
};

export type OpsSlaItem = {
  job_name: string;
  source: string;
  dataset: string;
  wave: string;
  total_runs: number;
  successful_runs: number;
  success_rate: number;
  p95_duration_seconds: number | null;
  avg_duration_seconds: number | null;
  latest_started_at_utc: string | null;
};

export type OpsSlaResponse = {
  include_blocked_as_success: boolean;
  min_total_runs: number;
  items: OpsSlaItem[];
};

export type OpsTimeseriesBucket = {
  bucket_start_utc: string;
  total: number;
  by_status: Record<string, number>;
};

export type OpsTimeseriesResponse = {
  entity: "runs" | "checks";
  granularity: "day" | "hour";
  items: OpsTimeseriesBucket[];
};

export type TerritoryItem = {
  territory_id: string;
  level: string;
  name: string;
  uf: string | null;
  municipality_ibge_code: string | null;
};

export type IndicatorItem = {
  fact_id: string;
  territory_id: string;
  source: string;
  dataset: string;
  indicator_code: string;
  indicator_name: string;
  value: number | null;
  reference_period: string;
  updated_at: string;
};

export type QgMetadata = {
  source_name: string;
  updated_at: string | null;
  coverage_note: string;
  unit: string | null;
  notes: string | null;
};

export type KpiOverviewItem = {
  domain: string;
  indicator_code: string;
  indicator_name: string;
  value: number;
  unit: string | null;
  delta: number | null;
  status: string;
  territory_level: string;
};

export type KpiOverviewResponse = {
  period: string | null;
  metadata: QgMetadata;
  items: KpiOverviewItem[];
};

export type PrioritySummaryResponse = {
  period: string | null;
  metadata: QgMetadata;
  total_items: number;
  by_status: Record<string, number>;
  by_domain: Record<string, number>;
  top_territories: string[];
};

export type PriorityEvidence = {
  indicator_code: string;
  reference_period: string;
  source: string;
  dataset: string;
};

export type PriorityItem = {
  territory_id: string;
  territory_name: string;
  territory_level: string;
  domain: string;
  indicator_code: string;
  indicator_name: string;
  value: number;
  unit: string | null;
  score: number;
  trend: string;
  status: "critical" | "attention" | "stable" | string;
  rationale: string[];
  evidence: PriorityEvidence;
};

export type PriorityListResponse = {
  period: string | null;
  level: string | null;
  domain: string | null;
  metadata: QgMetadata;
  items: PriorityItem[];
};

export type InsightEvidence = {
  indicator_code: string;
  reference_period: string;
  source: string;
  dataset: string;
};

export type InsightHighlightItem = {
  title: string;
  severity: "info" | "attention" | "critical";
  domain: string;
  territory_id: string;
  territory_name: string;
  explanation: string[];
  evidence: InsightEvidence;
  robustness: string;
};

export type InsightHighlightsResponse = {
  period: string | null;
  domain: string | null;
  severity: "info" | "attention" | "critical" | null;
  metadata: QgMetadata;
  items: InsightHighlightItem[];
};

export type ScenarioSimulateRequest = {
  territory_id: string;
  period?: string;
  level?: string;
  domain?: string;
  indicator_code?: string;
  adjustment_percent: number;
};

export type ScenarioSimulateResponse = {
  territory_id: string;
  territory_name: string;
  territory_level: string;
  period: string | null;
  domain: string;
  indicator_code: string;
  indicator_name: string;
  base_value: number;
  simulated_value: number;
  delta_value: number;
  adjustment_percent: number;
  base_score: number;
  simulated_score: number;
  peer_count: number;
  base_rank: number;
  simulated_rank: number;
  rank_delta: number;
  status_before: string;
  status_after: string;
  impact: "worsened" | "improved" | "unchanged" | string;
  metadata: QgMetadata;
  explanation: string[];
};

export type BriefGenerateRequest = {
  period?: string;
  level?: string;
  territory_id?: string;
  domain?: string;
  limit?: number;
};

export type BriefEvidenceItem = {
  territory_id: string;
  territory_name: string;
  territory_level: string;
  domain: string;
  indicator_code: string;
  indicator_name: string;
  value: number;
  unit: string | null;
  score: number;
  status: string;
  source: string;
  dataset: string;
  reference_period: string;
};

export type BriefGenerateResponse = {
  brief_id: string;
  title: string;
  generated_at: string;
  period: string | null;
  level: string | null;
  territory_id: string | null;
  domain: string | null;
  summary_lines: string[];
  recommended_actions: string[];
  evidences: BriefEvidenceItem[];
  metadata: QgMetadata;
};

export type TerritoryProfileIndicator = {
  indicator_code: string;
  indicator_name: string;
  value: number;
  unit: string | null;
  reference_period: string;
  status: string;
};

export type TerritoryProfileDomain = {
  domain: string;
  status: string;
  score: number | null;
  indicators_count: number;
  indicators: TerritoryProfileIndicator[];
};

export type TerritoryProfileResponse = {
  territory_id: string;
  territory_name: string;
  territory_level: string;
  period: string | null;
  overall_score: number | null;
  overall_status: string;
  overall_trend: "up" | "down" | "flat" | string;
  metadata: QgMetadata;
  highlights: string[];
  domains: TerritoryProfileDomain[];
};

export type TerritoryCompareItem = {
  domain: string;
  indicator_code: string;
  indicator_name: string;
  unit: string | null;
  reference_period: string;
  base_value: number;
  compare_value: number;
  delta: number;
  delta_percent: number | null;
  direction: "up" | "down" | "flat";
};

export type TerritoryCompareResponse = {
  territory_id: string;
  territory_name: string;
  compare_with_id: string;
  compare_with_name: string;
  period: string | null;
  metadata: QgMetadata;
  items: TerritoryCompareItem[];
};

export type TerritoryPeerItem = {
  territory_id: string;
  territory_name: string;
  territory_level: string;
  similarity_score: number;
  shared_indicators: number;
  avg_score: number | null;
  status: string;
};

export type TerritoryPeersResponse = {
  territory_id: string;
  territory_name: string;
  territory_level: string;
  period: string | null;
  metadata: QgMetadata;
  items: TerritoryPeerItem[];
};

export type ElectorateBreakdownItem = {
  label: string;
  voters: number;
  share_percent: number;
};

export type ElectorateSummaryResponse = {
  level: string;
  year: number | null;
  metadata: QgMetadata;
  total_voters: number;
  turnout: number | null;
  turnout_rate: number | null;
  abstention_rate: number | null;
  blank_rate: number | null;
  null_rate: number | null;
  by_sex: ElectorateBreakdownItem[];
  by_age: ElectorateBreakdownItem[];
  by_education: ElectorateBreakdownItem[];
};

export type ElectorateMapItem = {
  territory_id: string;
  territory_name: string;
  territory_level: string;
  metric: "voters" | "turnout" | "abstention_rate" | "blank_rate" | "null_rate";
  value: number | null;
  year: number | null;
  geometry: Record<string, unknown> | null;
};

export type ElectorateMapResponse = {
  level: string;
  metric: "voters" | "turnout" | "abstention_rate" | "blank_rate" | "null_rate";
  year: number | null;
  metadata: QgMetadata;
  items: ElectorateMapItem[];
};

export type ChoroplethItem = {
  territory_id: string;
  territory_name: string;
  level: string;
  metric: string;
  reference_period: string;
  value: number | null;
  geometry: Record<string, unknown> | null;
};
