import { requestJson } from "./http";
import type {
  BriefGenerateRequest,
  BriefGenerateResponse,
  ElectorateCandidateTerritoriesResponse,
  ElectorateElectionContextResponse,
  ElectorateHistoryResponse,
  ElectorateMapResponse,
  ElectoratePollingPlacesResponse,
  ElectorateSummaryResponse,
  InsightHighlightsResponse,
  KpiOverviewResponse,
  ScenarioSimulateRequest,
  ScenarioSimulateResponse,
  PriorityListResponse,
  PrioritySummaryResponse,
  TerritoryCompareResponse,
  TerritoryPeersResponse,
  TerritoryProfileResponse
} from "./types";

export function getKpisOverview(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<KpiOverviewResponse>("/kpis/overview", { query });
}

export function getPrioritySummary(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PrioritySummaryResponse>("/priority/summary", { query });
}

export function getPriorityList(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PriorityListResponse>("/priority/list", { query });
}

export function getInsightsHighlights(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<InsightHighlightsResponse>("/insights/highlights", { query });
}

export function getTerritoryProfile(
  territoryId: string,
  query?: Record<string, string | number | boolean | undefined>
) {
  return requestJson<TerritoryProfileResponse>(`/territory/${territoryId}/profile`, { query });
}

export function getTerritoryCompare(
  territoryId: string,
  query?: Record<string, string | number | boolean | undefined>
) {
  return requestJson<TerritoryCompareResponse>(`/territory/${territoryId}/compare`, { query });
}

export function getTerritoryPeers(
  territoryId: string,
  query?: Record<string, string | number | boolean | undefined>
) {
  return requestJson<TerritoryPeersResponse>(`/territory/${territoryId}/peers`, { query });
}

export function getElectorateSummary(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<ElectorateSummaryResponse>("/electorate/summary", { query });
}

export function getElectorateHistory(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<ElectorateHistoryResponse>("/electorate/history", { query });
}

export function getElectoratePollingPlaces(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<ElectoratePollingPlacesResponse>("/electorate/polling-places", { query });
}

export function getElectorateElectionContext(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<ElectorateElectionContextResponse>("/electorate/election-context", { query });
}

export function getElectorateCandidateTerritories(query: Record<string, string | number | boolean | undefined>) {
  return requestJson<ElectorateCandidateTerritoriesResponse>("/electorate/candidate-territories", { query });
}

export function getElectorateMap(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<ElectorateMapResponse>("/electorate/map", { query });
}

export function postScenarioSimulate(payload: ScenarioSimulateRequest) {
  return requestJson<ScenarioSimulateResponse>("/scenarios/simulate", {
    method: "POST",
    body: payload,
  });
}

export function postBriefGenerate(payload: BriefGenerateRequest) {
  return requestJson<BriefGenerateResponse>("/briefs", {
    method: "POST",
    body: payload,
  });
}
