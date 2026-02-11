import { requestJson } from "./http";
import type {
  ConnectorRegistryItem,
  FrontendEventItem,
  OpsSlaResponse,
  OpsSummaryResponse,
  OpsTimeseriesResponse,
  PaginatedResponse,
  PipelineCheck,
  PipelineRun
} from "./types";

export function getOpsSummary(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<OpsSummaryResponse>("/ops/summary", { query });
}

export function getOpsSla(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<OpsSlaResponse>("/ops/sla", { query });
}

export function getOpsTimeseries(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<OpsTimeseriesResponse>("/ops/timeseries", { query });
}

export function getPipelineRuns(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PaginatedResponse<PipelineRun>>("/ops/pipeline-runs", { query });
}

export function getPipelineChecks(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PaginatedResponse<PipelineCheck>>("/ops/pipeline-checks", { query });
}

export function getConnectorRegistry(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PaginatedResponse<ConnectorRegistryItem>>("/ops/connector-registry", { query });
}

export function getFrontendEvents(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PaginatedResponse<FrontendEventItem>>("/ops/frontend-events", { query });
}
