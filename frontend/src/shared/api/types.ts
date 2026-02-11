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
