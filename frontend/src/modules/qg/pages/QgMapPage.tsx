import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import type maplibregl from "maplibre-gl";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { getChoropleth, getMapLayers, getMapLayersCoverage, getMapStyleMetadata } from "../../../shared/api/domain";
import { formatApiError } from "../../../shared/api/http";
import { getElectorateMap } from "../../../shared/api/qg";
import type { MapLayerItem } from "../../../shared/api/types";
import { useAutoLayerSwitch } from "../../../shared/hooks/useAutoLayerSwitch";
import { formatDecimal, formatLevelLabel, formatStatusLabel, formatTrendLabel, toNumber } from "../../../shared/ui/presentation";
import { StateBlock } from "../../../shared/ui/StateBlock";
import type { VectorMapFeatureSelection, VizMode, OverlayLayerConfig, GeoJsonClusterConfig } from "../../../shared/ui/VectorMap";
import { useFilterStore } from "../../../shared/stores/filterStore";
import { emitTelemetry } from "../../../shared/observability/telemetry";

const TILE_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000/v1";
const BASEMAP_STREETS_URL =
  (import.meta.env.VITE_MAP_BASEMAP_STREETS_URL as string | undefined) ??
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

const VIZ_MODES: { value: VizMode; label: string }[] = [
  { value: "choropleth", label: "Coropletico" },
  { value: "points", label: "Pontos" },
];

type LayerScope = "territorial" | "urban";
type LayerClassification = "official" | "proxy" | "hybrid";
type ElectoralLayerView = "secao" | "local_votacao";
type MapOperationalState =
  | "loading"
  | "error"
  | "empty"
  | "empty_simplified_unavailable"
  | "empty_svg_urban_unavailable"
  | "data";

const LazyVectorMap = lazy(async () => {
  const module = await import("../../../shared/ui/VectorMap");
  return { default: module.VectorMap };
});

const FALLBACK_URBAN_LAYER_ITEMS: MapLayerItem[] = [
  {
    id: "urban_roads",
    label: "Viario urbano",
    territory_level: "urban",
    is_official: false,
    source: "map.urban_road_segment",
    default_visibility: true,
    zoom_min: 12,
    zoom_max: null,
    official_status: "hybrid",
    layer_kind: "line",
    notes: "Segmentos viarios para navegacao territorial detalhada.",
  },
  {
    id: "urban_pois",
    label: "Pontos de interesse",
    territory_level: "urban",
    is_official: false,
    source: "map.urban_poi",
    default_visibility: true,
    zoom_min: 12,
    zoom_max: null,
    official_status: "hybrid",
    layer_kind: "point",
    notes: "Equipamentos e servicos urbanos para leitura operacional.",
  },
];

function formatNumber(value: unknown) {
  const numeric = toNumber(value);
  if (numeric === null) {
    return "-";
  }
  return formatDecimal(numeric);
}

function inferStatusFromValue(value: unknown): "critical" | "attention" | "stable" | null {
  const numeric = toNumber(value);
  if (numeric === null) {
    return null;
  }
  if (numeric >= 80) {
    return "stable";
  }
  if (numeric >= 60) {
    return "attention";
  }
  return "critical";
}

function optionalText(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  const token = String(value).trim();
  if (!token) {
    return null;
  }
  return token;
}

function buildApiHref(path: string, params: Record<string, string | number | null | undefined>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined) {
      continue;
    }
    search.set(key, String(value));
  }
  const queryString = search.toString();
  return `${TILE_BASE_URL}${path}${queryString ? `?${queryString}` : ""}`;
}

function normalizeText(value: string) {
  return value.trim().toLowerCase();
}

function resolveElectoralLayerView(level: string, layerId: string): ElectoralLayerView | null {
  if (level !== "electoral_section") {
    return null;
  }
  if (layerId === "territory_polling_place") {
    return "local_votacao";
  }
  if (layerId === "territory_electoral_section") {
    return "secao";
  }
  return null;
}

function normalizeMapLevel(value: string | null) {
  const normalized = (value ?? "").trim().toLowerCase();
  if (normalized === "municipio" || normalized === "municipality") {
    return "municipio";
  }
  if (normalized === "distrito" || normalized === "district") {
    return "distrito";
  }
  if (normalized === "setor_censitario" || normalized === "census_sector") {
    return "setor_censitario";
  }
  if (normalized === "zona_eleitoral" || normalized === "electoral_zone") {
    return "zona_eleitoral";
  }
  if (normalized === "secao_eleitoral" || normalized === "electoral_section") {
    return "secao_eleitoral";
  }
  return "municipio";
}

function toManifestTerritoryLevel(level: string) {
  if (level === "distrito") {
    return "district";
  }
  if (level === "setor_censitario") {
    return "census_sector";
  }
  if (level === "zona_eleitoral") {
    return "electoral_zone";
  }
  if (level === "secao_eleitoral") {
    return "electoral_section";
  }
  return "municipality";
}

function toFormLevel(level: string) {
  if (level === "district") {
    return "distrito";
  }
  if (level === "census_sector") {
    return "setor_censitario";
  }
  if (level === "electoral_zone") {
    return "zona_eleitoral";
  }
  if (level === "electoral_section") {
    return "secao_eleitoral";
  }
  return "municipio";
}

function supportsChoropleth(level: string) {
  return level === "municipio" || level === "distrito";
}

function toPriorityLevel(level: string) {
  if (level === "distrito") {
    return "district";
  }
  return "municipality";
}

function normalizeVizMode(value: string | null): VizMode {
  const normalized = (value ?? "").trim().toLowerCase();
  if (normalized === "points" || normalized === "heatmap" || normalized === "critical" || normalized === "gap") {
    return normalized;
  }
  return "choropleth";
}

function normalizeZoom(value: string | null, fallback: number) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(0, Math.min(18, Math.round(parsed)));
}

function recommendedZoomByLevel(level: string) {
  if (level === "distrito") return 10;
  if (level === "setor_censitario") return 13;
  if (level === "zona_eleitoral") return 11;
  if (level === "secao_eleitoral") return 14;
  return 8;
}

function resolveStrategicYear(period: string) {
  const parsed = Number.parseInt(period, 10);
  if (!Number.isFinite(parsed) || parsed < 1994 || parsed > 2100) {
    return 2024;
  }
  return parsed;
}

function resolveContextualZoom(
  currentZoom: number,
  scope: LayerScope,
  level: string,
  preferredLayer?: MapLayerItem,
) {
  const baseline = scope === "urban" ? 12 : recommendedZoomByLevel(level);
  const layerZoomMin = Math.max(baseline, preferredLayer?.zoom_min ?? baseline);
  if (currentZoom < layerZoomMin) {
    return Math.max(0, Math.min(18, layerZoomMin));
  }
  return Math.max(0, Math.min(18, currentZoom));
}

function normalizeScope(value: string | null, layerId: string | null): LayerScope {
  const normalized = (value ?? "").trim().toLowerCase();
  if (normalized === "urban" || normalized === "urbano") {
    return "urban";
  }
  if ((layerId ?? "").startsWith("urban_")) {
    return "urban";
  }
  return "territorial";
}

function normalizeUrbanLayerId(value: string | null): string {
  return value === "urban_pois" ? "urban_pois" : "urban_roads";
}

function formatScopeLabel(scope: LayerScope) {
  return scope === "urban" ? "Urbana" : "Territorial";
}

type LayerGroup = {
  key: "territorio" | "eleitoral" | "servicos";
  title: string;
  items: Array<{ id: string; label: string; subtitle?: string; active: boolean; toggleable?: boolean }>;
};

const MAP_LEVEL_ORDER: string[] = [
  "municipality",
  "district",
  "census_sector",
  "electoral_zone",
  "electoral_section",
];

function sortLayerLevels(a: string, b: string) {
  const aIndex = MAP_LEVEL_ORDER.indexOf(a);
  const bIndex = MAP_LEVEL_ORDER.indexOf(b);
  if (aIndex === -1 && bIndex === -1) {
    return a.localeCompare(b);
  }
  if (aIndex === -1) {
    return 1;
  }
  if (bIndex === -1) {
    return -1;
  }
  return aIndex - bIndex;
}

function formatZoomRange(zoomMin: number, zoomMax: number | null) {
  if (zoomMax === null) {
    return `z>=${zoomMin}`;
  }
  return `z${zoomMin}-${zoomMax}`;
}

function resolveLayerClassification(layer?: Pick<MapLayerItem, "official_status" | "is_official"> | null): LayerClassification | null {
  if (!layer) {
    return null;
  }
  const normalized = (layer.official_status ?? "").trim().toLowerCase();
  if (normalized === "official" || normalized === "proxy" || normalized === "hybrid") {
    return normalized;
  }
  return layer.is_official ? "official" : "proxy";
}

function formatLayerClassificationLabel(layer?: Pick<MapLayerItem, "official_status" | "is_official"> | null): string {
  const classification = resolveLayerClassification(layer);
  if (classification === "official") {
    return "oficial";
  }
  if (classification === "proxy") {
    return "proxy";
  }
  if (classification === "hybrid") {
    return "hibrida";
  }
  return "n/d";
}

function buildLayerClassificationHint(layer?: MapLayerItem | null): string {
  const classification = resolveLayerClassification(layer);
  if (classification === "proxy") {
    return (
      layer?.proxy_method ??
      layer?.notes ??
      "Camada proxy derivada de agregacao espacial; validar limites antes de decisoes criticas."
    );
  }
  if (classification === "hybrid") {
    return layer?.notes ?? "Camada hibrida com composição de fontes oficiais e auxiliares.";
  }
  if (classification === "official") {
    return layer?.notes ?? "Camada oficial baseada em recorte territorial institucional.";
  }
  return layer?.notes ?? "Camada sem metadata adicional.";
}

function csvEscape(value: string) {
  const escaped = value.split('"').join('""');
  return `"${escaped}"`;
}

function sanitizeFilePart(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "mapa";
}

function formatVectorMapError(rawMessage: string) {
  const token = rawMessage.trim();
  if (!token) {
    return "Falha temporaria no modo vetorial. Tente novamente ou use o fallback SVG.";
  }
  const normalized = token.toLowerCase();
  if (normalized.includes("service unavailable") || normalized.includes("503")) {
    return "Camada vetorial temporariamente indisponível (503). O mapa continua ativo; tente novamente em instantes.";
  }
  return `Falha temporaria no modo vetorial: ${token}`;
}

function triggerDownload(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export function QgMapPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const globalFilters = useFilterStore();
  const initialMetric = "MTE_NOVO_CAGED_SALDO_TOTAL";
  const initialPeriod = "2025";
  const initialLevel = normalizeMapLevel(searchParams.get("level"));
  const initialTerritoryId = searchParams.get("territory_id") || undefined;
  const initialLayerId = searchParams.get("layer_id") || null;
  const initialVizMode = normalizeVizMode(searchParams.get("viz"));
  const initialScope = normalizeScope(searchParams.get("scope"), initialLayerId);
  const initialUrbanLayerId = normalizeUrbanLayerId(initialLayerId);
  const initialZoom = resolveContextualZoom(
    normalizeZoom(searchParams.get("zoom"), globalFilters.zoom),
    initialScope,
    initialLevel,
  );

  const [metric, setMetric] = useState(initialMetric);
  const [period, setPeriod] = useState(initialPeriod);
  const [level, setLevel] = useState<string>(initialLevel);
  const [mapScope, setMapScope] = useState<LayerScope>(initialScope);
  const [appliedMetric, setAppliedMetric] = useState(initialMetric);
  const [appliedPeriod, setAppliedPeriod] = useState(initialPeriod);
  const [appliedLevel, setAppliedLevel] = useState<string>(initialLevel);
  const [appliedMapScope, setAppliedMapScope] = useState<LayerScope>(initialScope);
  const [urbanLayerId, setUrbanLayerId] = useState<string>(initialUrbanLayerId);
  const [appliedUrbanLayerId, setAppliedUrbanLayerId] = useState<string>(initialUrbanLayerId);
  const [selectedTerritoryId, setSelectedTerritoryId] = useState<string | undefined>(initialTerritoryId);
  const [exportError, setExportError] = useState<string | null>(null);
  const [vectorMapError, setVectorMapError] = useState<string | null>(null);
  const [currentZoom, setCurrentZoom] = useState(initialZoom);
  const [vizMode, setVizMode] = useState<VizMode>(initialVizMode);
  const basemapMode = "streets" as const;
  const [selectedFeature, setSelectedFeature] = useState<VectorMapFeatureSelection | null>(null);
  const [territoryPanelCollapsed, setTerritoryPanelCollapsed] = useState(false);
  const [territorySearch, setTerritorySearch] = useState("");
  const [territoryFocusNotice, setTerritoryFocusNotice] = useState<string | null>(null);
  const [mapRecenterNotice, setMapRecenterNotice] = useState<string | null>(null);
  const [focusSignal, setFocusSignal] = useState(initialTerritoryId ? 1 : 0);
  const [resetViewSignal, setResetViewSignal] = useState(0);
  const [layerSelectionNotice, setLayerSelectionNotice] = useState<string | null>(null);
  const [selectedVectorLayerId, setSelectedVectorLayerId] = useState<string | null>(
    initialScope === "territorial" ? initialLayerId : null,
  );
  const previousAppliedLevelRef = useRef(appliedLevel);
  const previousZoomRef = useRef(initialZoom);
  const previousVizModeRef = useRef(initialVizMode);
  const previousLayerKeyRef = useRef<string>("");
  const previousElectoralLayerViewRef = useRef<ElectoralLayerView | null>(null);
  const previousMapOperationalStateRef = useRef<MapOperationalState | null>(null);
  const previousVectorErrorRef = useRef<string | null>(null);

  const [activeOverlayIds, setActiveOverlayIds] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    globalFilters.setZoom(initialZoom);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isChoroplethLevel = supportsChoropleth(appliedLevel);
  const shouldFetchChoropleth = appliedMapScope === "territorial" && isChoroplethLevel;

  const choroplethParams = useMemo(
    () => ({
      metric: appliedMetric,
      period: appliedPeriod,
      level: appliedLevel,
      page: 1,
      page_size: 1000,
    }),
    [appliedLevel, appliedMetric, appliedPeriod],
  );

  const choroplethQuery = useQuery({
    queryKey: ["qg", "map", choroplethParams],
    queryFn: () => getChoropleth(choroplethParams),
    enabled: shouldFetchChoropleth,
  });

  const mapLayersQuery = useQuery({
    queryKey: ["qg", "map", "layers", "include_urban"],
    queryFn: () => getMapLayers({ include_urban: true }),
    staleTime: 5 * 60 * 1000,
  });

  const mapStyleQuery = useQuery({
    queryKey: ["qg", "map", "style-metadata"],
    queryFn: () => getMapStyleMetadata(),
    staleTime: 5 * 60 * 1000,
  });

  const layersCoverageQuery = useQuery({
    queryKey: ["qg", "map", "layers", "coverage", appliedMetric, appliedPeriod, "include_urban"],
    queryFn: () => getMapLayersCoverage({ metric: appliedMetric, period: appliedPeriod, include_urban: true }),
    staleTime: 60 * 1000,
  });

  const appliedStrategicYear = useMemo(() => resolveStrategicYear(appliedPeriod), [appliedPeriod]);
  const isPollingPlacesOverlayEnabled = activeOverlayIds.has("overlay_polling_places");
  const shouldFetchPollingPlaces = isPollingPlacesOverlayEnabled;

  const electorateSectionQuery = useQuery({
    queryKey: ["qg", "map", "electorate-sections", appliedStrategicYear, "with-geometry"],
    queryFn: () =>
      getElectorateMap({
        level: "secao_eleitoral",
        year: appliedStrategicYear,
        metric: "voters",
        aggregate_by: "polling_place",
        include_geometry: true,
        limit: 500,
      }),
    enabled: shouldFetchPollingPlaces,
    staleTime: 60 * 1000,
  });

  const electorateSectionFallbackQuery = useQuery({
    queryKey: ["qg", "map", "electorate-sections", "fallback", 2024, "with-geometry"],
    queryFn: () =>
      getElectorateMap({
        level: "secao_eleitoral",
        year: 2024,
        metric: "voters",
        aggregate_by: "polling_place",
        include_geometry: true,
        limit: 500,
      }),
    enabled:
      shouldFetchPollingPlaces &&
      appliedStrategicYear !== 2024 &&
      !electorateSectionQuery.isPending &&
      !electorateSectionQuery.error &&
      (electorateSectionQuery.data?.items.length ?? 0) === 0,
    staleTime: 60 * 1000,
  });

  const effectiveElectorateSectionData =
    (electorateSectionQuery.data?.items.length ?? 0) > 0
      ? electorateSectionQuery.data
      : electorateSectionFallbackQuery.data ?? electorateSectionQuery.data;
  const mapLayersError = mapLayersQuery.error ? formatApiError(mapLayersQuery.error) : null;
  const mapStyleError = mapStyleQuery.error ? formatApiError(mapStyleQuery.error) : null;
  const layersCoverageError = layersCoverageQuery.error ? formatApiError(layersCoverageQuery.error) : null;
  const styleMetadata = mapStyleQuery.data?.generated_at_utc ?? null;

  const territorialLayers = useMemo(
    () => (mapLayersQuery.data?.items ?? []).filter((item) => item.territory_level !== "urban"),
    [mapLayersQuery.data?.items],
  );
  const urbanLayers = useMemo(
    () => (mapLayersQuery.data?.items ?? []).filter((item) => item.territory_level === "urban"),
    [mapLayersQuery.data?.items],
  );

  const availableFormLevels = useMemo<string[]>(() => {
    const levels = Array.from(new Set(territorialLayers.map((item) => item.territory_level)));
    return levels.sort(sortLayerLevels).map((item) => toFormLevel(item));
  }, [territorialLayers]);

  useEffect(() => {
    if (mapScope !== "territorial") {
      return;
    }
    if (availableFormLevels.length === 0) {
      return;
    }
    if (!availableFormLevels.includes(level)) {
      setLevel(availableFormLevels[0]);
    }
    if (!availableFormLevels.includes(appliedLevel)) {
      setAppliedLevel(availableFormLevels[0]);
    }
  }, [appliedLevel, availableFormLevels, level, mapScope]);

  const activeTerritoryLevel = toManifestTerritoryLevel(appliedLevel);
  const levelScopedLayers = useMemo(
    () => territorialLayers.filter((layerItem) => layerItem.territory_level === activeTerritoryLevel),
    [activeTerritoryLevel, territorialLayers],
  );
  const resolvedDefaultLayerId =
    levelScopedLayers.find((layerItem) => layerItem.default_visibility)?.id ??
    levelScopedLayers[0]?.id ??
    mapLayersQuery.data?.default_layer_id;

  const autoLayer = useAutoLayerSwitch(
    levelScopedLayers.length > 0 ? levelScopedLayers : territorialLayers,
    currentZoom,
    resolvedDefaultLayerId,
  );

  const normalizedItems = useMemo(
    () =>
      (shouldFetchChoropleth ? choroplethQuery.data?.items ?? [] : []).map((item) => ({
        ...item,
        value: toNumber(item.value),
      })),
    [choroplethQuery.data?.items, shouldFetchChoropleth],
  );

  const sortedItems = useMemo(
    () =>
      [...normalizedItems].sort(
        (a, b) => (b.value ?? Number.NEGATIVE_INFINITY) - (a.value ?? Number.NEGATIVE_INFINITY),
      ),
    [normalizedItems],
  );

  useEffect(() => {
    if (appliedMapScope !== "territorial" || !selectedTerritoryId) {
      return;
    }
    const selected = sortedItems.find((item) => item.territory_id === selectedTerritoryId);
    if (selected) {
      setTerritorySearch(selected.territory_name);
    }
  }, [appliedMapScope, selectedTerritoryId, sortedItems]);

  const availableLevelLayerIds = useMemo(() => new Set(levelScopedLayers.map((item) => item.id)), [levelScopedLayers]);
  const availableUrbanLayers = urbanLayers.length > 0 ? urbanLayers : FALLBACK_URBAN_LAYER_ITEMS;
  const selectedUrbanLayer =
    availableUrbanLayers.find((layerItem) => layerItem.id === appliedUrbanLayerId) ?? availableUrbanLayers[0]!;
  const canUseVectorMap = appliedMapScope === "urban" ? Boolean(selectedUrbanLayer) : Boolean(resolvedDefaultLayerId);
  const selectedLayerCoverage =
    appliedMapScope === "territorial"
      ? layersCoverageQuery.data?.items.find((item) => item.territory_level === activeTerritoryLevel)
      : layersCoverageQuery.data?.items.find((item) => item.layer_id === selectedUrbanLayer.id);
  const telemetryRecommendedLayer =
    appliedMapScope === "urban"
      ? selectedUrbanLayer
      : levelScopedLayers.find((layerItem) => layerItem.default_visibility) ?? levelScopedLayers[0] ?? null;
  const telemetryExplicitLayer =
    appliedMapScope === "territorial" && selectedVectorLayerId
      ? levelScopedLayers.find((layerItem) => layerItem.id === selectedVectorLayerId) ?? null
      : null;
  const telemetryEffectiveLayer =
    appliedMapScope === "urban" ? selectedUrbanLayer : telemetryExplicitLayer ?? autoLayer ?? telemetryRecommendedLayer;
  const telemetryEffectiveLayerId = telemetryEffectiveLayer?.id ?? "n/d";
  const telemetryEffectiveLayerClassification = formatLayerClassificationLabel(telemetryEffectiveLayer);
  const mapOperationalState: MapOperationalState = shouldFetchChoropleth && choroplethQuery.isPending
    ? "loading"
    : shouldFetchChoropleth && Boolean(choroplethQuery.error)
      ? "error"
      : appliedMapScope === "territorial" && isChoroplethLevel && sortedItems.length === 0
        ? "empty"
        : "data";

  useEffect(() => {
    setVectorMapError(null);
  }, [appliedLevel, appliedMetric, appliedPeriod]);

  useEffect(() => {
    if (appliedMapScope !== "territorial") {
      setLayerSelectionNotice(null);
      return;
    }
    if (selectedVectorLayerId) {
      setLayerSelectionNotice(null);
    }
  }, [appliedMapScope, selectedVectorLayerId]);

  useEffect(() => {
    if (appliedMapScope !== "territorial") {
      return;
    }
    if (!selectedVectorLayerId) {
      return;
    }
    if (levelScopedLayers.length === 0) {
      return;
    }
    if (!availableLevelLayerIds.has(selectedVectorLayerId)) {
      setSelectedVectorLayerId(null);
      setLayerSelectionNotice("Camada detalhada anterior indisponível para o nivel atual; seleção automatica restaurada.");
    }
  }, [appliedMapScope, availableLevelLayerIds, levelScopedLayers.length, selectedVectorLayerId]);

  useEffect(() => {
    if (appliedMapScope !== "territorial") {
      return;
    }
    if (previousAppliedLevelRef.current !== appliedLevel) {
      if (selectedVectorLayerId) {
        setLayerSelectionNotice("Nível territorial alterado; camada detalhada reiniciada para recomendacao automatica.");
      }
      setSelectedVectorLayerId(null);
    }
    previousAppliedLevelRef.current = appliedLevel;
  }, [appliedLevel, appliedMapScope, selectedVectorLayerId]);

  useEffect(() => {
    const nextSearch = new URLSearchParams();
    nextSearch.set("zoom", String(currentZoom));

    if (appliedMapScope === "urban") {
      nextSearch.set("scope", "urban");
      nextSearch.set("layer_id", appliedUrbanLayerId);
    } else {
      nextSearch.set("level", appliedLevel);
      if (selectedVectorLayerId) {
        nextSearch.set("layer_id", selectedVectorLayerId);
      }
    }

    if (selectedTerritoryId && appliedMapScope === "territorial") {
      nextSearch.set("territory_id", selectedTerritoryId);
    }
    if (basemapMode !== "streets") {
      nextSearch.set("basemap", basemapMode);
    }
    if (vizMode !== "choropleth") {
      nextSearch.set("viz", vizMode);
    }
    const nextValue = nextSearch.toString();
    const currentValue = searchParams.toString();
    if (nextValue !== currentValue) {
      setSearchParams(nextSearch, { replace: true });
    }
  }, [
    appliedLevel,
    appliedMapScope,
    appliedUrbanLayerId,
    basemapMode,
    currentZoom,
    searchParams,
    selectedTerritoryId,
    selectedVectorLayerId,
    setSearchParams,
    vizMode,
  ]);

  function handleZoomChange(newZoom: number) {
    setCurrentZoom(newZoom);
    globalFilters.setZoom(newZoom);
  }

  useEffect(() => {
    if (previousZoomRef.current === currentZoom) {
      return;
    }
    emitTelemetry({
      category: "performance",
      name: "map_zoom_changed",
      severity: "info",
      attributes: {
        zoom: currentZoom,
        scope: appliedMapScope,
        level: appliedLevel,
        metric: appliedMetric,
        period: appliedPeriod,
      },
    });
    previousZoomRef.current = currentZoom;
  }, [appliedLevel, appliedMapScope, appliedMetric, appliedPeriod, currentZoom]);

  useEffect(() => {
    if (previousVizModeRef.current === vizMode) {
      return;
    }
    emitTelemetry({
      category: "lifecycle",
      name: "map_mode_changed",
      severity: "info",
      attributes: {
        viz_mode: vizMode,
        scope: appliedMapScope,
        level: appliedLevel,
      },
    });
    previousVizModeRef.current = vizMode;
  }, [appliedLevel, appliedMapScope, vizMode]);

  useEffect(() => {
    const nextLayerKey = [appliedMapScope, appliedLevel, telemetryEffectiveLayerId].join("::");
    if (previousLayerKeyRef.current === nextLayerKey) {
      return;
    }
    emitTelemetry({
      category: "lifecycle",
      name: "map_layer_changed",
      severity: "info",
      attributes: {
        scope: appliedMapScope,
        level: appliedLevel,
        layer_id: telemetryEffectiveLayerId,
        layer_classification: telemetryEffectiveLayerClassification,
      },
    });
    previousLayerKeyRef.current = nextLayerKey;
  }, [appliedLevel, appliedMapScope, telemetryEffectiveLayerClassification, telemetryEffectiveLayerId]);

  useEffect(() => {
    const currentElectoralLayerView = resolveElectoralLayerView(activeTerritoryLevel, telemetryEffectiveLayerId);
    const previousElectoralLayerView = previousElectoralLayerViewRef.current;

    if (!currentElectoralLayerView) {
      previousElectoralLayerViewRef.current = null;
      return;
    }

    if (!previousElectoralLayerView) {
      previousElectoralLayerViewRef.current = currentElectoralLayerView;
      return;
    }

    if (previousElectoralLayerView === currentElectoralLayerView) {
      return;
    }

    emitTelemetry({
      category: "lifecycle",
      name: "map_electoral_layer_toggled",
      severity: "info",
      attributes: {
        scope: appliedMapScope,
        level: appliedLevel,
        from_layer: previousElectoralLayerView,
        to_layer: currentElectoralLayerView,
        layer_id: telemetryEffectiveLayerId,
        layer_classification: telemetryEffectiveLayerClassification,
        source: selectedVectorLayerId ? "manual" : "automatica",
      },
    });

    previousElectoralLayerViewRef.current = currentElectoralLayerView;
  }, [
    activeTerritoryLevel,
    appliedLevel,
    appliedMapScope,
    selectedVectorLayerId,
    telemetryEffectiveLayerClassification,
    telemetryEffectiveLayerId,
  ]);

  useEffect(() => {
    if (previousMapOperationalStateRef.current === mapOperationalState) {
      return;
    }
    emitTelemetry({
      category: "lifecycle",
      name: "map_operational_state_changed",
      severity: "info",
      attributes: {
        scope: appliedMapScope,
        level: appliedLevel,
        state: mapOperationalState,
        renderer: "advanced",
        metric: appliedMetric,
        period: appliedPeriod,
      },
    });
    previousMapOperationalStateRef.current = mapOperationalState;
  }, [appliedLevel, appliedMapScope, appliedMetric, appliedPeriod, mapOperationalState]);

  useEffect(() => {
    if (!vectorMapError || previousVectorErrorRef.current === vectorMapError) {
      return;
    }
    emitTelemetry({
      category: "frontend_error",
      name: "map_tile_error",
      severity: "error",
      attributes: {
        message: vectorMapError,
        scope: appliedMapScope,
        level: appliedLevel,
        layer_id: telemetryEffectiveLayerId,
      },
    });
    previousVectorErrorRef.current = vectorMapError;
  }, [appliedLevel, appliedMapScope, telemetryEffectiveLayerId, vectorMapError]);

  // --- Build GeoJSON FeatureCollection for electoral sections ---
  const sectionGeoJson = useMemo<GeoJSON.FeatureCollection>(() => {
    const items = effectiveElectorateSectionData?.items ?? [];
    const validItems = items.filter(
      (item) => item.geometry && typeof item.value === "number" && item.value > 0,
    );
    const totalVoters = validItems.reduce((sum, item) => sum + (item.value ?? 0), 0);
    return {
      type: "FeatureCollection" as const,
      features: validItems.map((item) => {
        const sections = Array.isArray(item.sections)
          ? item.sections.map((section) => String(section)).filter(Boolean)
          : [];

        return {
          type: "Feature" as const,
          properties: {
            tid: item.territory_id,
            tname: item.territory_name,
            polling_place_name: item.polling_place_name ?? item.territory_name,
            polling_place_code: item.polling_place_code ?? null,
            section_count: item.section_count ?? 0,
            sections,
            sections_csv: sections.join(", "),
            voters: item.value ?? 0,
            voters_pct: totalVoters > 0 ? Number(((item.value ?? 0) / totalVoters * 100).toFixed(2)) : 0,
          },
          geometry: item.geometry as unknown as GeoJSON.Geometry,
        };
      }),
    };
  }, [effectiveElectorateSectionData?.items]);

  const sectionTotalVoters = useMemo(() => {
    return sectionGeoJson.features.reduce(
      (sum, f) => sum + ((f.properties as Record<string, unknown>)?.voters as number ?? 0),
      0,
    );
  }, [sectionGeoJson]);

  // --- GeoJSON cluster config for electoral sections ---
  const sectionClusterConfig: GeoJsonClusterConfig | null = useMemo(() => {
    if (sectionGeoJson.features.length === 0) return null;
    if (!activeOverlayIds.has("overlay_polling_places")) return null;
    return {
      id: "electoral-sections",
      data: sectionGeoJson,
      color: "#1e40af",
      opacity: 0.65,
      strokeColor: "#fff",
      strokeWidth: 1.5,
      radiusExpression: [
        "max", 4, ["min", 18, ["*", 0.35, ["sqrt", ["coalesce", ["get", "voters"], 1]]]],
      ] as unknown as maplibregl.ExpressionSpecification,
      clusterRadius: 50,
      clusterMaxZoom: 12,
      clusterProperties: {
        sum_voters: ["+", ["get", "voters"]],
      },
      clusterLabelExpression: [
        "concat",
        ["to-string", ["get", "point_count"]],
        " locais\n",
        ["to-string", ["get", "sum_voters"]],
        " eleitores",
      ] as unknown as maplibregl.ExpressionSpecification,
      tooltipFn: (props: Record<string, unknown>) => {
        const name = String(props.polling_place_name ?? props.tname ?? "n/d");
        const voters = Number(props.voters ?? 0);
        const pct = Number(props.voters_pct ?? 0);
        const sectionCount =
          typeof props.section_count === "number"
            ? props.section_count
            : Number(props.section_count ?? 0);
        const sectionsRaw = Array.isArray(props.sections)
          ? props.sections.map((item) => String(item)).filter(Boolean)
          : [];
        const sectionsCsv = typeof props.sections_csv === "string"
          ? props.sections_csv.split(",").map((item) => item.trim()).filter(Boolean)
          : [];
        const sectionsResolved = sectionsRaw.length > 0 ? sectionsRaw : sectionsCsv;
        const sections = sectionsResolved.slice(0, 6);
        return [
          `<strong>Local: ${name}</strong>`,
          `Eleitores: ${voters.toLocaleString("pt-BR")}`,
          `Qtd seções: ${sectionCount}`,
          sections.length > 0 ? `Seções: ${sections.join(", ")}${sectionsResolved.length > sections.length ? " ..." : ""}` : "Seções: n/d",
          `% do município: ${pct.toFixed(1)}%`,
          `Fonte: TSE | Eleitorado`,
        ].join("<br/>");
      },
      clusterTooltipFn: (props: Record<string, unknown>) => {
        const count = Number(props.point_count ?? 0);
        const sumVoters = Number(props.sum_voters ?? 0);
        return [
          `<strong>${count} locais agrupados</strong>`,
          `Total: ${sumVoters.toLocaleString("pt-BR")} eleitores`,
        ].join("<br/>");
      },
      enabled: true,
    };
  }, [activeOverlayIds, sectionGeoJson]);

  // Resolve whether boundary-only mode is on
  const isBoundaryOnly = true;


  function focusTerritoryFromSearch() {
    if (appliedMapScope !== "territorial" || sortedItems.length === 0) {
      return;
    }
    const searchValue = normalizeText(territorySearch);
    const match =
      sortedItems.find((item) => normalizeText(item.territory_name) === searchValue) ??
      sortedItems.find((item) => normalizeText(item.territory_name).includes(searchValue)) ??
      sortedItems[0];
    if (!match) {
      return;
    }
    setSelectedTerritoryId(match.territory_id);
    setTerritorySearch(match.territory_name);
    setTerritoryFocusNotice(null);
    setMapRecenterNotice(null);
    setFocusSignal((value) => value + 1);
  }

  function focusSelectedTerritory() {
    if (!selectedTerritoryId) {
      return;
    }
    setTerritoryFocusNotice(null);
    setMapRecenterNotice(null);
    setFocusSignal((value) => value + 1);
  }

  function recenterMap(clearNotice = true) {
    if (clearNotice) {
      setTerritoryFocusNotice(null);
      setMapRecenterNotice(null);
    }
    setResetViewSignal((value) => value + 1);
  }

  function applyFilters() {
    const hadTerritoryContext = Boolean(selectedTerritoryId || selectedFeature || territorySearch.trim());
    const scopeChanged = mapScope !== appliedMapScope;
    const levelChanged = level !== appliedLevel;
    const formTerritoryLevel = toManifestTerritoryLevel(level);
    const formLevelLayers = territorialLayers.filter((layerItem) => layerItem.territory_level === formTerritoryLevel);
    const formPreferredTerritorialLayer =
      formLevelLayers.find((layerItem) => layerItem.default_visibility) ?? formLevelLayers[0];
    const formPreferredUrbanLayer =
      availableUrbanLayers.find((layerItem) => layerItem.id === urbanLayerId) ?? availableUrbanLayers[0];
    const preferredLayer = mapScope === "urban" ? formPreferredUrbanLayer : formPreferredTerritorialLayer;
    const nextZoom = resolveContextualZoom(currentZoom, mapScope, level, preferredLayer);

    setAppliedMetric(metric);
    setAppliedPeriod(period);
    setAppliedLevel(level);
    setAppliedMapScope(mapScope);
    setAppliedUrbanLayerId(urbanLayerId);
    setSelectedTerritoryId(undefined);
    setTerritorySearch("");
    setSelectedFeature(null);
    if (hadTerritoryContext) {
      setTerritoryFocusNotice("Filtros aplicados; foco territorial anterior reiniciado.");
    } else {
      setTerritoryFocusNotice(null);
    }
    if (mapScope === "urban") {
      setSelectedVectorLayerId(null);
    }
    setExportError(null);
    setVectorMapError(null);
    if (nextZoom !== currentZoom) {
      setCurrentZoom(nextZoom);
      globalFilters.setZoom(nextZoom);
    }
    const zoomChanged = nextZoom !== currentZoom;
    const shouldRecenter = scopeChanged || levelChanged || zoomChanged;
    if (shouldRecenter) {
      setMapRecenterNotice("Filtros aplicados; mapa recentrado automaticamente para manter contexto do recorte.");
      recenterMap(false);
    } else {
      setMapRecenterNotice(null);
    }
  }

  function applyStrategicPreset(preset: "electoral_sections" | "urban_services") {
    setSelectedFeature(null);
    setSelectedTerritoryId(undefined);
    setTerritorySearch("");
    setLayerSelectionNotice(null);
    setTerritoryFocusNotice(null);
    setExportError(null);
    setVectorMapError(null);

    if (preset === "electoral_sections") {
      const nextPeriod = /^\d{4}$/.test(period) ? period : "2024";
      setMapScope("territorial");
      setLevel("secao_eleitoral");
      setPeriod(nextPeriod);
      setAppliedMapScope("territorial");
      setAppliedLevel("secao_eleitoral");
      setAppliedPeriod(nextPeriod);
      setSelectedVectorLayerId("territory_electoral_section");
      const nextZoom = Math.max(currentZoom, 14);
      setCurrentZoom(nextZoom);
      globalFilters.setZoom(nextZoom);
      setMapRecenterNotice("Preset aplicado: seções eleitorais com foco no volume de eleitores por secao.");
      recenterMap(false);
      return;
    }

    setMapScope("urban");
    setUrbanLayerId("urban_pois");
    setAppliedMapScope("urban");
    setAppliedUrbanLayerId("urban_pois");
    setSelectedVectorLayerId(null);
    setVizMode("points");
    const nextZoom = Math.max(currentZoom, 12);
    setCurrentZoom(nextZoom);
    globalFilters.setZoom(nextZoom);
    setMapRecenterNotice("Preset aplicado: servicos urbanos para leitura territorial por bairros e proximidade.");
    recenterMap(false);
  }

  function clearFilters() {
    const hadTerritoryContext = Boolean(selectedTerritoryId || selectedFeature || territorySearch.trim());
    setMetric("MTE_NOVO_CAGED_SALDO_TOTAL");
    setPeriod("2025");
    setLevel("municipio");
    setMapScope("territorial");
    setAppliedMapScope("territorial");
    setUrbanLayerId("urban_roads");
    setAppliedUrbanLayerId("urban_roads");
    setAppliedMetric("MTE_NOVO_CAGED_SALDO_TOTAL");
    setAppliedPeriod("2025");
    setAppliedLevel("municipio");
    setSelectedTerritoryId(undefined);
    setTerritorySearch("");
    setSelectedFeature(null);
    if (hadTerritoryContext) {
      setTerritoryFocusNotice("Filtros limpos; foco territorial reiniciado.");
    } else {
      setTerritoryFocusNotice(null);
    }
    setExportError(null);
    setVectorMapError(null);
    setVizMode("choropleth");
    setCurrentZoom(4);
    globalFilters.setZoom(4);
    setMapRecenterNotice("Filtros limpos; mapa recentrado para a visao inicial.");
    recenterMap(false);
  }

  function exportCsv() {
    if (!sortedItems.length) {
      return;
    }
    const rows = [
      ["territory_id", "territory_name", "level", "metric", "reference_period", "value"],
      ...sortedItems.map((item) => [
        item.territory_id,
        item.territory_name,
        item.level,
        item.metric,
        item.reference_period,
        item.value === null ? "" : String(item.value),
      ]),
    ];
    const csv = rows.map((row) => row.map(csvEscape).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    triggerDownload(blob, "qg_mapa_ranking.csv");
  }

  function resolveMapSvgElement() {
    const node = document.querySelector(".choropleth-svg");
    if (node instanceof SVGSVGElement) {
      return node;
    }
    return null;
  }

  function serializeMapSvg() {
    const svg = resolveMapSvgElement();
    if (!svg) {
      return null;
    }
    const serializer = new XMLSerializer();
    let source = serializer.serializeToString(svg);
    if (!source.includes("xmlns=")) {
      source = source.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"');
    }
    if (!source.includes("xmlns:xlink=")) {
      source = source.replace("<svg", '<svg xmlns:xlink="http://www.w3.org/1999/xlink"');
    }
    return { svg, source };
  }

  function exportMapSvg() {
    setExportError(null);
    const serialized = serializeMapSvg();
    if (!serialized) {
      setExportError("Não foi possível localizar o mapa para exportacao.");
      return;
    }
    const metricPart = sanitizeFilePart(appliedMetric);
    const periodPart = sanitizeFilePart(appliedPeriod);
    const fileName = `qg_mapa_${metricPart}_${periodPart}.svg`;
    const blob = new Blob([serialized.source], { type: "image/svg+xml;charset=utf-8" });
    triggerDownload(blob, fileName);
  }

  function exportMapPng() {
    setExportError(null);
    const serialized = serializeMapSvg();
    if (!serialized) {
      setExportError("Não foi possível localizar o mapa para exportacao.");
      return;
    }

    const { svg, source } = serialized;
    const viewBox = svg.viewBox?.baseVal;
    const width = Math.max(1, Math.round(viewBox?.width || 820));
    const height = Math.max(1, Math.round(viewBox?.height || 420));

    const svgBlob = new Blob([source], { type: "image/svg+xml;charset=utf-8" });
    const svgUrl = URL.createObjectURL(svgBlob);
    const image = new Image();

    image.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext("2d");
        if (!context) {
          setExportError("Não foi possível preparar o canvas para exportacao.");
          URL.revokeObjectURL(svgUrl);
          return;
        }
        context.fillStyle = "#f6f4ee";
        context.fillRect(0, 0, width, height);
        context.drawImage(image, 0, 0, width, height);
        canvas.toBlob((blob) => {
          URL.revokeObjectURL(svgUrl);
          if (!blob) {
            setExportError("Falha ao converter o mapa para PNG.");
            return;
          }
          const metricPart = sanitizeFilePart(appliedMetric);
          const periodPart = sanitizeFilePart(appliedPeriod);
          const fileName = `qg_mapa_${metricPart}_${periodPart}.png`;
          triggerDownload(blob, fileName);
        }, "image/png");
      } catch (_error) {
        URL.revokeObjectURL(svgUrl);
        setExportError("Falha ao exportar PNG no navegador atual.");
      }
    };

    image.onerror = () => {
      URL.revokeObjectURL(svgUrl);
      setExportError("Falha ao carregar imagem temporaria para exportacao.");
    };

    image.src = svgUrl;
  }

  if (shouldFetchChoropleth && choroplethQuery.isPending) {
    return <StateBlock tone="loading" title="Carregando mapa" message="Consultando distribuição territorial do indicador." />;
  }

  if (shouldFetchChoropleth && choroplethQuery.error) {
    const { message, requestId } = formatApiError(choroplethQuery.error);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar mapa"
        message={message}
        requestId={requestId}
        onRetry={() => void choroplethQuery.refetch()}
      />
    );
  }

  const selectedItem =
    appliedMapScope === "territorial"
      ? sortedItems.find((item) => item.territory_id === selectedTerritoryId) ?? sortedItems[0]
      : undefined;
  const recommendedLayer =
    appliedMapScope === "urban"
      ? selectedUrbanLayer
      : levelScopedLayers.find((layerItem) => layerItem.default_visibility) ?? levelScopedLayers[0];
  const hasMultipleLevelLayers = appliedMapScope === "territorial" && levelScopedLayers.length > 1;
  const explicitLayer =
    appliedMapScope === "territorial" && selectedVectorLayerId
      ? levelScopedLayers.find((layerItem) => layerItem.id === selectedVectorLayerId) ?? null
      : null;
  const effectiveLayer = appliedMapScope === "urban" ? selectedUrbanLayer : explicitLayer ?? autoLayer ?? recommendedLayer;
  const contextualZoomFloor = resolveContextualZoom(0, appliedMapScope, appliedLevel, effectiveLayer);
  const vectorLayers = appliedMapScope === "urban" ? [selectedUrbanLayer] : effectiveLayer ? [effectiveLayer] : levelScopedLayers;
  const effectiveVizMode: VizMode =
    effectiveLayer?.layer_kind === "point" && vizMode === "choropleth" ? "points" : vizMode;
  const isElectoralSectionLevel = appliedMapScope === "territorial" && activeTerritoryLevel === "electoral_section";
  const pollingPlaceLayer = isElectoralSectionLevel
    ? levelScopedLayers.find((layerItem) => layerItem.id === "territory_polling_place") ?? null
    : null;
  const hasPollingPlaceLayer = Boolean(pollingPlaceLayer);
  const sectionGeometryLayer = isElectoralSectionLevel
    ? levelScopedLayers.find((layerItem) => layerItem.id === "territory_electoral_section") ?? null
    : null;
  const isPollingPlaceActive = effectiveLayer?.id === "territory_polling_place";
  const canTogglePollingLayer = Boolean(isElectoralSectionLevel && hasPollingPlaceLayer && sectionGeometryLayer);
  const pollingLayerToggleTargetId = isPollingPlaceActive
    ? sectionGeometryLayer?.id ?? null
    : pollingPlaceLayer?.id ?? null;
  const effectiveVizLabel = VIZ_MODES.find((mode) => mode.value === effectiveVizMode)?.label ?? effectiveVizMode;

  const selectedTerritoryName = selectedItem?.territory_name ?? selectedFeature?.tname;
  const selectedTerritoryValue = selectedItem?.value ?? selectedFeature?.val;
  const selectedTerritoryIdSafe = selectedItem?.territory_id ?? selectedFeature?.tid;
  const selectedFeatureLabel = selectedFeature?.label ?? selectedTerritoryName;
  const selectedPollingPlaceName =
    optionalText(selectedFeature?.rawProperties?.local_votacao) ??
    optionalText(selectedFeature?.rawProperties?.polling_place_name) ??
    (isPollingPlaceActive ? optionalText(selectedFeature?.label) : null);
  const pollingPlaceAvailabilityNote = !isElectoralSectionLevel
    ? null
    : !hasPollingPlaceLayer
      ? "local_votacao: indisponível no manifesto atual"
      : isPollingPlaceActive
        ? selectedPollingPlaceName
          ? `local_votacao: detectado (${selectedPollingPlaceName})`
          : "local_votacao: camada ativa sem nome detectado na feição selecionada"
        : "local_votacao: disponível (altere para Locais de votação para detalhar o ponto)";
  const topTerritory = sortedItems[0] ?? null;
  const bottomTerritory = sortedItems.length > 1 ? sortedItems[sortedItems.length - 1] ?? null : null;
  const selectedTerritoryRank =
    selectedItem && sortedItems.length > 0
      ? sortedItems.findIndex((item) => item.territory_id === selectedItem.territory_id) + 1
      : null;
  const recommendedLayerClassification = formatLayerClassificationLabel(recommendedLayer);
  const effectiveLayerClassification = formatLayerClassificationLabel(effectiveLayer);
  const effectiveLayerHint = buildLayerClassificationHint(effectiveLayer);
  const effectiveLayerSourceLabel = selectedVectorLayerId ? "manual" : "automatica";
  const selectedFeatureCategory = selectedFeature?.category ?? null;
  const selectedFeatureQueryText = optionalText(selectedFeatureLabel ?? selectedTerritoryName);
  const selectedFeatureSubcategory = optionalText(selectedFeature?.rawProperties?.subcategory);
  const selectedFeatureSource = optionalText(selectedFeature?.rawProperties?.source);
  const selectedFeatureRoadClass = optionalText(selectedFeature?.rawProperties?.road_class);
  const selectedFeatureLon = typeof selectedFeature?.lon === "number" ? selectedFeature.lon : null;
  const selectedFeatureLat = typeof selectedFeature?.lat === "number" ? selectedFeature.lat : null;
  const selectedFeatureMetadata = Object.entries(selectedFeature?.rawProperties ?? {})
    .filter(([key]) => !["tid", "tname", "val", "value", "geometry", "geom"].includes(key))
    .filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== "")
    .slice(0, 6);
  const selectedFeatureSections = Array.isArray(selectedFeature?.rawProperties?.sections)
    ? (selectedFeature?.rawProperties?.sections as unknown[]).map((section) => String(section)).filter(Boolean)
    : typeof selectedFeature?.rawProperties?.sections_csv === "string"
      ? selectedFeature.rawProperties.sections_csv
          .split(",")
          .map((section) => section.trim())
          .filter(Boolean)
      : [];
  const selectedFeatureSectionCount =
    typeof selectedFeature?.rawProperties?.section_count === "number" ||
    typeof selectedFeature?.rawProperties?.section_count === "string"
      ? Number(selectedFeature.rawProperties.section_count)
      : selectedFeatureSections.length;
  const drawerTerritoryItem =
    appliedMapScope === "territorial"
      ? sortedItems.find((item) => item.territory_id === selectedTerritoryId) ?? sortedItems[0]
      : undefined;
  const drawerTerritoryId = drawerTerritoryItem?.territory_id ?? selectedFeature?.tid ?? null;
  const drawerTerritoryName = drawerTerritoryItem?.territory_name ?? selectedFeature?.tname ?? null;
  const drawerTerritoryValue = drawerTerritoryItem?.value ?? selectedFeature?.val ?? null;
  const drawerStatusRaw = optionalText(selectedFeature?.rawProperties?.status);
  const drawerStatusFallback = inferStatusFromValue(drawerTerritoryValue);
  const drawerTrendRaw = optionalText(selectedFeature?.rawProperties?.trend);
  const drawerScoreDisplay = formatNumber(drawerTerritoryValue);
  const drawerStatusDisplay = drawerStatusRaw
    ? formatStatusLabel(drawerStatusRaw)
    : drawerStatusFallback
      ? formatStatusLabel(drawerStatusFallback)
      : "n/d";
  const drawerTrendDisplay = drawerTrendRaw ? formatTrendLabel(drawerTrendRaw) : "n/d";
  const drawerCoverageDisplay = selectedLayerCoverage
    ? `${selectedLayerCoverage.territories_with_geometry}/${selectedLayerCoverage.territories_total}`
    : "n/d";
  const drawerEvidenceItems = selectedFeatureMetadata.slice(0, 4);
  const sectionElectorateTopItems = effectiveElectorateSectionData
    ? [...effectiveElectorateSectionData.items]
        .filter((item) => typeof item.value === "number")
        .sort((a, b) => (b.value ?? Number.NEGATIVE_INFINITY) - (a.value ?? Number.NEGATIVE_INFINITY))
        .slice(0, 5)
    : [];
  const hasSingleMunicipalityView =
    appliedMapScope === "territorial" && appliedLevel === "municipio" && sortedItems.length <= 1;

  const selectedTerritoryActions = appliedMapScope === "territorial" && selectedTerritoryIdSafe
    ? {
        profile: `/territorio/${encodeURIComponent(selectedTerritoryIdSafe)}`,
        scenarios: `/cenarios?territory_id=${encodeURIComponent(selectedTerritoryIdSafe)}&period=${encodeURIComponent(
          appliedPeriod,
        )}`,
        briefs: `/briefs?territory_id=${encodeURIComponent(selectedTerritoryIdSafe)}&period=${encodeURIComponent(
          appliedPeriod,
        )}`,
      }
    : null;
  const selectedUrbanActions =
    appliedMapScope === "urban" && selectedFeature
      ? {
          scopedCollection:
            selectedUrbanLayer.id === "urban_pois"
              ? buildApiHref("/map/urban/pois", {
                  category: selectedFeatureCategory,
                  limit: 200,
                })
              : buildApiHref("/map/urban/roads", {
                  road_class: selectedFeatureRoadClass ?? selectedFeatureCategory,
                  limit: 200,
                }),
          geocode: selectedFeatureQueryText
            ? buildApiHref("/map/urban/geocode", {
                q: selectedFeatureQueryText,
                kind: selectedUrbanLayer.id === "urban_pois" ? "poi" : "road",
                limit: 20,
              })
            : null,
          nearbyPois:
            selectedFeatureLon !== null && selectedFeatureLat !== null
              ? buildApiHref("/map/urban/nearby-pois", {
                  lon: selectedFeatureLon.toFixed(6),
                  lat: selectedFeatureLat.toFixed(6),
                  radius_m: 1200,
                  category: selectedUrbanLayer.id === "urban_pois" ? selectedFeatureCategory : null,
                  limit: 50,
                })
              : null,
          scopedLabel:
            selectedUrbanLayer.id === "urban_pois" ? "Filtrar POIs desta categoria" : "Filtrar vias desta classe",
        }
      : null;

  const strategicLayerGroups: LayerGroup[] = [
    {
      key: "territorio",
      title: "Território",
      items: [
        {
          id: "boundary_municipal",
          label: "Limite municipal",
          active: true,
        },
      ],
    },
    {
      key: "eleitoral",
      title: "Eleitoral",
      items: [
        {
          id: "overlay_polling_places",
          label: "Locais de votação",
          active: activeOverlayIds.has("overlay_polling_places"),
          toggleable: true,
        },
      ],
    },
    {
      key: "servicos",
      title: "Serviços",
      items: [
        {
          id: "overlay_schools",
          label: "Escolas",
          active: activeOverlayIds.has("overlay_schools"),
          toggleable: true,
        },
        {
          id: "overlay_ubs",
          label: "UBS / Saúde",
          active: activeOverlayIds.has("overlay_ubs"),
          toggleable: true,
        },
      ],
    },

  ];

  function toggleOverlay(overlayId: string) {
    const willEnable = !activeOverlayIds.has(overlayId);
    setActiveOverlayIds((prev) => {
      const next = new Set(prev);
      if (next.has(overlayId)) {
        next.delete(overlayId);
      } else {
        next.add(overlayId);
      }
      return next;
    });

    if (overlayId !== "overlay_polling_places" || !willEnable) {
      return;
    }

    const pollingPlacePreferredLayer =
      territorialLayers.find((layerItem) => layerItem.id === "territory_polling_place") ??
      territorialLayers.find((layerItem) => layerItem.territory_level === "electoral_section") ??
      undefined;

    const nextZoom = resolveContextualZoom(currentZoom, "territorial", "secao_eleitoral", pollingPlacePreferredLayer);

    setMapScope("territorial");
    setAppliedMapScope("territorial");
    setLevel("secao_eleitoral");
    setAppliedLevel("secao_eleitoral");
    setSelectedVectorLayerId(null);
    setLayerSelectionNotice("Locais de votação ativado; mapa ajustado automaticamente para seção eleitoral.");

    if (nextZoom !== currentZoom) {
      setCurrentZoom(nextZoom);
      globalFilters.setZoom(nextZoom);
      setMapRecenterNotice("Mapa ajustado para seção eleitoral para exibir locais de votação.");
      setResetViewSignal((value) => value + 1);
    }
  }

  const overlayConfigs: OverlayLayerConfig[] = [
    {
      id: "overlay_schools",
      label: "Escolas",
      tileLayerId: "urban_pois",
      vizType: "circle",
      color: "#f59e0b",
      filter: ["==", ["get", "category"], "education"] as unknown as maplibregl.ExpressionSpecification,
      enabled: activeOverlayIds.has("overlay_schools"),
      opacity: 0.85,
      minZoom: 10,
    },
    {
      id: "overlay_ubs",
      label: "UBS / Saúde",
      tileLayerId: "urban_pois",
      vizType: "circle",
      color: "#ef4444",
      filter: ["==", ["get", "category"], "health"] as unknown as maplibregl.ExpressionSpecification,
      enabled: activeOverlayIds.has("overlay_ubs"),
      opacity: 0.85,
      minZoom: 10,
    },
  ];

  // Assemble the geoJson layers array for VectorMap
  const activeGeoJsonLayers: GeoJsonClusterConfig[] = sectionClusterConfig ? [sectionClusterConfig] : [];

  return (
    <main className="page-map-executive">
      <header className="map-actions-bar">
        <div className="map-toolbar-block">
          <p className="map-toolbar-label">Mapa base</p>
          <div className="viz-mode-selector" aria-label="Mapa base">
            <button type="button" className="viz-mode-btn viz-mode-active" aria-pressed="true" disabled>
              OpenStreetMap
            </button>
          </div>
        </div>
        <div className="map-toolbar-block">
          <p className="map-toolbar-label">Exportar</p>
          <div className="map-toolbar-actions-row">
            <button type="button" className="button-secondary" onClick={exportMapSvg} aria-label="Exportar mapa como SVG">
              SVG
            </button>
            <button type="button" className="button-secondary" onClick={exportMapPng} aria-label="Exportar mapa como PNG">
              PNG
            </button>
          </div>
        </div>
      </header>

      <div className="map-search-bar">
        <input
          id="territory-search-input"
          list="territory-search-options"
          value={territorySearch}
          onChange={(event) => setTerritorySearch(event.target.value)}
          placeholder="Buscar território ou endereço..."
          aria-label="Buscar territorio"
        />
        <button type="button" className="button-secondary" onClick={focusTerritoryFromSearch} disabled={sortedItems.length === 0}>
          Buscar
        </button>
        <datalist id="territory-search-options">
          {sortedItems.map((item) => (
            <option key={item.territory_id} value={item.territory_name} />
          ))}
        </datalist>
      </div>

      {/* ── Row 3: Loading/error states (manifests/style) ── */}
      {mapLayersQuery.isPending && !mapLayersQuery.data ? (
        <StateBlock
          tone="loading"
          title="Carregando manifesto de camadas"
          message="Buscando catálogo territorial e urbano para configuração do mapa."
        />
      ) : mapLayersError ? (
        <StateBlock
          tone="error"
          title="Manifesto de camadas indisponível"
          message={`${mapLayersError.message}`}
          requestId={mapLayersError.requestId}
          onRetry={() => void mapLayersQuery.refetch()}
        />
      ) : null}
      {mapStyleQuery.isPending && !mapStyleQuery.data ? (
        <StateBlock
          tone="loading"
          title="Carregando metadados de estilo"
          message="Preparando paleta e faixas para legenda do mapa."
        />
      ) : mapStyleError ? (
        <StateBlock
          tone="error"
          title="Falha ao carregar metadados de estilo"
          message={`${mapStyleError.message} Legenda padrão mantida.`}
          requestId={mapStyleError.requestId}
          onRetry={() => void mapStyleQuery.refetch()}
        />
      ) : null}

      {/* ── Row 4: 2-column body (map 75% + sidebar 25%) ── */}
      <div className="map-with-sidebar">
        <div className="map-canvas-shell">
          {canUseVectorMap ? (
            <Suspense
              fallback={
                <StateBlock
                  tone="loading"
                  title="Carregando mapa avançado"
                  message="Preparando camadas vetoriais e base cartográfica."
                />
              }
            >
              <LazyVectorMap
                tileBaseUrl={TILE_BASE_URL}
                layers={vectorLayers.length > 0 ? vectorLayers : levelScopedLayers}
                defaultLayerId={effectiveLayer?.id ?? resolvedDefaultLayerId ?? selectedUrbanLayer.id}
                vizMode={effectiveVizMode}
                zoom={currentZoom}
                onZoomChange={(z) => handleZoomChange(z)}
                onFeatureClick={(feature) => {
                  setTerritoryPanelCollapsed(false);
                  setSelectedTerritoryId(feature.tid || undefined);
                  setSelectedFeature(feature);
                  setTerritorySearch(feature.tname ?? "");
                }}
                onError={(message) => {
                  const nextError = formatVectorMapError(message);
                  setVectorMapError((current) => (current === nextError ? current : nextError));
                }}
                selectedTerritoryId={selectedTerritoryId}
                focusTerritorySignal={focusSignal}
                resetViewSignal={resetViewSignal}
                colorStops={mapStyleQuery.data?.legend_ranges?.map((range) => ({
                  value: range.min_value,
                  color: range.color,
                }))}
                basemapMode={basemapMode}
                basemapTileUrls={{
                  streets: BASEMAP_STREETS_URL,
                }}
                tooltipContext={{
                  indicatorName: appliedMetric,
                  trend: drawerTrendRaw,
                  source: effectiveLayer?.source ?? "n/d",
                  updatedAt: styleMetadata,
                }}
                overlays={overlayConfigs}
                geoJsonLayers={activeGeoJsonLayers}
                boundaryOnly={isBoundaryOnly}
                showContextLabels={!isPollingPlacesOverlayEnabled && appliedLevel !== "secao_eleitoral"}
              />
            </Suspense>
          ) : (
            <StateBlock
              tone="empty"
              title="Camada indisponível"
              message="Nenhuma camada vetorial disponível para o recorte atual."
            />
          )}
        </div>
        <aside className="map-layers-sidebar" aria-label="Painel de camadas estrategicas">
          <h3>Camadas</h3>
          {strategicLayerGroups.map((group) => (
            <div key={group.key} className="map-layers-sidebar-group">
              <h4>{group.title}</h4>
              <ul>
                {group.items.map((item) => (
                  <li key={item.id}>
                    <label className="overlay-toggle-label">
                      <input
                        type="checkbox"
                        checked={item.active}
                        onChange={item.toggleable ? () => toggleOverlay(item.id) : undefined}
                        disabled={!item.toggleable}
                        aria-label={`Ativar camada ${item.label}`}
                      />
                      <span className="overlay-toggle-text">{item.label}</span>
                      {item.subtitle ? <span className="overlay-toggle-subtitle">{item.subtitle}</span> : null}
                    </label>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <div className="map-layers-sidebar-search-actions">
            <button type="button" className="button-secondary" onClick={focusTerritoryFromSearch} disabled={sortedItems.length === 0}>
              Focar
            </button>
            <button type="button" className="button-secondary" onClick={() => recenterMap()}>
              Resetar
            </button>
          </div>
        </aside>
      </div>

      {/* ── Row 6: Collapsible bottom area (Ranking / Detalhes tabs) ── */}
      <details className="map-bottom-panel">
        <summary className="map-bottom-panel-summary">
          <span className="map-bottom-tab">Ranking</span>
          <span className="map-bottom-tab">Detalhes do território</span>
        </summary>
        <div className="map-bottom-panel-content">
          {/* Ranking section */}
          <section className="map-bottom-section" aria-label="Ranking territorial">
            <div className="map-bottom-section-header">
              <h3>Ranking territorial</h3>
              <button
                type="button"
                className="button-secondary"
                onClick={exportCsv}
                disabled={sortedItems.length === 0}
                aria-label="Exportar ranking como CSV"
              >
                CSV
              </button>
            </div>
            {appliedMapScope === "urban" ? (
              <StateBlock tone="empty" title="Ranking indisponível para camada urbana" message="Use o modo avançado para explorar camadas urbanas." />
            ) : !isChoroplethLevel ? (
              <StateBlock tone="empty" title="Ranking indisponível neste nivel" message="Use o nivel municipio ou distrito para ranking tabular." />
            ) : sortedItems.length === 0 ? (
              <StateBlock tone="empty" title="Sem dados" message="Nenhum territorio encontrado para o recorte informado." />
            ) : (
              <div className="table-wrap">
                <table aria-label="Ranking territorial">
                  <thead>
                    <tr>
                      <th>Território</th>
                      <th>Nível</th>
                      <th>Período</th>
                      <th>Valor</th>
                      <th>Acao</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedItems.map((item) => (
                      <tr
                        key={item.territory_id}
                        className={item.territory_id === selectedTerritoryId ? "territory-selected-row" : undefined}
                        onClick={() => {
                          setTerritoryPanelCollapsed(false);
                          setSelectedTerritoryId(item.territory_id);
                          setTerritorySearch(item.territory_name);
                          setFocusSignal((value) => value + 1);
                        }}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            setTerritoryPanelCollapsed(false);
                            setSelectedTerritoryId(item.territory_id);
                            setTerritorySearch(item.territory_name);
                            setFocusSignal((value) => value + 1);
                          }
                        }}
                        tabIndex={0}
                        role="button"
                        aria-pressed={item.territory_id === selectedTerritoryId}
                      >
                        <td>{item.territory_name}</td>
                        <td>{formatLevelLabel(item.level)}</td>
                        <td>{item.reference_period}</td>
                        <td>{formatNumber(item.value)}</td>
                        <td>
                          <Link
                            className="inline-link"
                            to={`/territorio/${item.territory_id}`}
                            onClick={(event) => {
                              event.preventDefault();
                              event.stopPropagation();
                              void navigate(`/territorio/${item.territory_id}`);
                            }}
                          >
                            Abrir perfil
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Territory detail section */}
          {drawerTerritoryName ? (
            <section className="map-bottom-section" aria-label="Detalhe territorial">
              <div className="map-bottom-section-header">
                <h3>{drawerTerritoryName}</h3>
                <span className="map-bottom-section-subtitle">
                  {formatLevelLabel(appliedLevel)} · {drawerStatusDisplay} · {drawerTrendDisplay}
                </span>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => {
                    setTerritoryPanelCollapsed(true);
                    setSelectedFeature(null);
                    setSelectedTerritoryId(undefined);
                  }}
                  aria-label="Fechar painel territorial"
                >
                  Fechar
                </button>
              </div>

              <div className="territory-detail-grid">
                <div className="territory-detail-score-card">
                  <p>Valor</p>
                  <strong>{drawerScoreDisplay}</strong>
                </div>
                <div className="territory-detail-stats" role="list" aria-label="Metricas rápidas do territorio">
                  <article role="listitem">
                    <span>Período</span>
                    <strong>{appliedPeriod}</strong>
                  </article>
                  <article role="listitem">
                    <span>Camada</span>
                    <strong>{effectiveLayer?.label ?? "n/d"}</strong>
                  </article>
                  <article role="listitem">
                    <span>Zoom</span>
                    <strong>z{currentZoom}</strong>
                  </article>
                </div>
              </div>

              {drawerEvidenceItems.length > 0 ? (
                <ul className="territory-detail-evidence-list">
                  {drawerEvidenceItems.map(([key, value]) => (
                    <li key={key}>
                      <strong>{key}:</strong> {String(value)}
                    </li>
                  ))}
                </ul>
              ) : null}

              {selectedFeatureSectionCount > 0 ? (
                <div className="territory-detail-section-list" aria-label="Seções do local de votacao">
                  <p className="territory-detail-section-title">Seções no local</p>
                  <p>{selectedFeatureSectionCount} seções</p>
                  {selectedFeatureSections.length > 0 ? <p>{selectedFeatureSections.join(", ")}</p> : null}
                </div>
              ) : null}

              {selectedTerritoryActions ? (
                <nav className="territory-detail-actions" aria-label="Acoes territoriais">
                  <Link className="button-secondary" to={selectedTerritoryActions.profile}>
                    Perfil 360
                  </Link>
                  <Link className="button-secondary" to={selectedTerritoryActions.scenarios}>
                    Cenarios
                  </Link>
                  <Link className="button-secondary" to={selectedTerritoryActions.briefs}>
                    Adicionar ao Brief
                  </Link>
                </nav>
              ) : null}

              {selectedUrbanActions ? (
                <nav className="territory-detail-actions" aria-label="Acoes urbanas">
                  <a className="button-secondary" href={selectedUrbanActions.scopedCollection} target="_blank" rel="noreferrer">
                    {selectedUrbanActions.scopedLabel}
                  </a>
                  {selectedUrbanActions.geocode ? (
                    <a className="button-secondary" href={selectedUrbanActions.geocode} target="_blank" rel="noreferrer">
                      Geocodificar
                    </a>
                  ) : null}
                  {selectedUrbanActions.nearbyPois ? (
                    <a className="button-secondary" href={selectedUrbanActions.nearbyPois} target="_blank" rel="noreferrer">
                      POIs proximos
                    </a>
                  ) : null}
                </nav>
              ) : null}
            </section>
          ) : null}
        </div>
      </details>
    </main>
  );
}
