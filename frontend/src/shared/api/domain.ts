import { requestJson } from "./http";
import type {
  ChoroplethItem,
  IndicatorItem,
  MapLayerMetadataResponse,
  MapLayersCoverageResponse,
  MapLayersResponse,
  MapStyleMetadataResponse,
  PaginatedResponse,
  TerritoryItem
} from "./types";

export function getTerritories(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PaginatedResponse<TerritoryItem>>("/territories", { query });
}

export function getIndicators(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PaginatedResponse<IndicatorItem>>("/indicators", { query });
}

export function getChoropleth(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<PaginatedResponse<ChoroplethItem>>("/geo/choropleth", { query });
}

export function getMapLayers(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<MapLayersResponse>("/map/layers", { query });
}

export function getMapLayersCoverage(query?: Record<string, string | number | boolean | undefined>) {
  return requestJson<MapLayersCoverageResponse>("/map/layers/coverage", { query });
}

export function getMapLayerMetadata(layerId: string) {
  return requestJson<MapLayerMetadataResponse>(`/map/layers/${layerId}/metadata`);
}

export function getMapStyleMetadata() {
  return requestJson<MapStyleMetadataResponse>("/map/style-metadata");
}
