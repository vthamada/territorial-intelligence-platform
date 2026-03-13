import { requestJson } from "./http";
import type {
  AdminSyncHistoryItem,
  AdminSyncJobEnvelopeResponse,
  AdminSyncJobStatus,
  AdminSyncStartRequest,
  ConnectorRegistryItem,
  FrontendEventItem,
  MapLayersReadinessResponse,
  OpsReadinessResponse,
  OpsSlaResponse,
  OpsSourceCoverageResponse,
  OpsSummaryResponse,
  OpsTimeseriesResponse,
  PaginatedResponse,
  PipelineCheck,
  PipelineRun
} from "./types";

const ADMIN_OPS_TOKEN = import.meta.env.VITE_ADMIN_OPS_TOKEN;

function getAdminOpsHeaders() {
  return ADMIN_OPS_TOKEN ? { "x-admin-ops-token": ADMIN_OPS_TOKEN } : undefined;
}

export function getOpsSummary(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<OpsSummaryResponse>("/ops/summary", { query });
}

export function getOpsSla(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<OpsSlaResponse>("/ops/sla", { query });
}

export function getOpsTimeseries(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<OpsTimeseriesResponse>("/ops/timeseries", { query });
}

export function getOpsSourceCoverage(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<OpsSourceCoverageResponse>("/ops/source-coverage", { query });
}

export function getOpsReadiness(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<OpsReadinessResponse>("/ops/readiness", { query });
}

export function getAdminSyncStatus() {
  return requestJson<AdminSyncJobEnvelopeResponse>("/ops/admin/sync/status", {
    headers: getAdminOpsHeaders(),
  });
}

export function getAdminSyncJob(jobId: string) {
  return requestJson<AdminSyncJobEnvelopeResponse>(`/ops/admin/sync/jobs/${jobId}`, {
    headers: getAdminOpsHeaders(),
  });
}

export function getAdminSyncHistory(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PaginatedResponse<AdminSyncHistoryItem>>("/ops/admin/sync/history", {
    query,
    headers: getAdminOpsHeaders(),
  });
}

export function startAdminSync(payload: AdminSyncStartRequest) {
  return requestJson<AdminSyncJobStatus>("/ops/admin/sync/start", {
    method: "POST",
    body: payload,
    headers: getAdminOpsHeaders(),
  });
}

export function getMapLayersReadiness(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<MapLayersReadinessResponse>("/map/layers/readiness", { query });
}

export function getTerritoryLayersReadiness(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<MapLayersReadinessResponse>("/territory/layers/readiness", { query });
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
