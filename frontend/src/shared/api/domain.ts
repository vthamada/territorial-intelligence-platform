import { requestJson } from "./http";
import type { IndicatorItem, PaginatedResponse, TerritoryItem } from "./types";

export function getTerritories(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PaginatedResponse<TerritoryItem>>("/territories", { query });
}

export function getIndicators(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PaginatedResponse<IndicatorItem>>("/indicators", { query });
}
