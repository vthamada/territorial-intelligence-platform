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

export type OpsSourceCoverageItem = {
  source: string;
  wave: string;
  implemented_connectors: number;
  runs_total: number;
  runs_success: number;
  runs_blocked: number;
  runs_failed: number;
  rows_loaded_total: number;
  latest_run_started_at_utc: string | null;
  latest_reference_period: string | null;
  fact_indicator_rows: number;
  fact_indicator_codes: number;
  latest_indicator_updated_at: string | null;
  coverage_status: "ready" | "idle" | "failed" | "blocked" | "no_fact_rows" | "partial" | string;
};

export type OpsSourceCoverageResponse = {
  source: string | null;
  wave: string | null;
  reference_period: string | null;
  include_internal: boolean;
  items: OpsSourceCoverageItem[];
};

export type OpsReadinessSloItem = {
  job_name: string;
  total_runs: number;
  successful_runs: number;
  success_rate_pct: number;
  meets_target: boolean;
};

export type OpsReadinessSlo = {
  window_days: number;
  target_pct: number;
  include_blocked_as_success: boolean;
  total_runs: number;
  successful_runs: number;
  success_rate_pct: number;
  meets_target: boolean;
  below_target_jobs: string[];
  items: OpsReadinessSloItem[];
  window_role?: "current_health" | string;
};

export type OpsReadinessResponse = {
  status: "READY" | "NOT_READY";
  strict: boolean;
  generated_at_utc: string;
  window_days: number;
  postgis: {
    installed: boolean;
    version: string | null;
  };
  required_tables: {
    required: Array<{ schema: string; table: string }>;
    found_count: number;
    missing: Array<{ schema: string; table: string }>;
  };
  connector_registry: {
    total: number;
    by_status: Record<string, number>;
    implemented_jobs: string[];
  };
  slo1: OpsReadinessSlo;
  slo1_current: OpsReadinessSlo;
  slo3: {
    window_days: number;
    total_runs: number;
    runs_with_checks: number;
    runs_missing_checks: number;
    meets_target: boolean;
    sample_missing_run_ids: string[];
  };
  source_probe: {
    total_rows: number;
    by_source: Record<string, number>;
  };
  hard_failures: string[];
  warnings: string[];
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
  source: string | null;
  dataset: string | null;
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

export type MapLayerItem = {
  id: string;
  label: string;
  territory_level: "municipality" | "district" | "census_sector" | string;
  is_official: boolean;
  source: string;
  default_visibility: boolean;
  zoom_min: number;
  zoom_max: number | null;
};

export type MapLayersResponse = {
  generated_at_utc: string;
  default_layer_id: string;
  fallback_endpoint: string;
  items: MapLayerItem[];
};

export type MapStyleSeverityItem = {
  severity: string;
  label: string;
  color: string;
};

export type MapStyleDomainItem = {
  domain: string;
  label: string;
  color: string;
};

export type MapStyleLegendRangeItem = {
  key: string;
  label: string;
  min_value: number;
  max_value: number;
  color: string;
};

export type MapStyleMetadataResponse = {
  generated_at_utc: string;
  version: string;
  default_mode: string;
  severity_palette: MapStyleSeverityItem[];
  domain_palette: MapStyleDomainItem[];
  legend_ranges: MapStyleLegendRangeItem[];
  notes: string;
};
