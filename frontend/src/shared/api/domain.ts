import { requestJson } from "./http";
import type { ChoroplethItem, IndicatorItem, MapLayersResponse, PaginatedResponse, TerritoryItem } from "./types";

export function getTerritories(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PaginatedResponse<TerritoryItem>>("/territories", { query });
}

export function getIndicators(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PaginatedResponse<IndicatorItem>>("/indicators", { query });
}

export function getChoropleth(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PaginatedResponse<ChoroplethItem>>("/geo/choropleth", { query });
}

export function getMapLayers() {
  return requestJson<MapLayersResponse>("/map/layers");
}
