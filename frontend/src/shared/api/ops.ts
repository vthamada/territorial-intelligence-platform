import { requestJson } from "./http";
import type {
  OpsSlaResponse,
  OpsSummaryResponse,
  OpsTimeseriesResponse,
  PaginatedResponse,
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
