import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { getChoropleth, getMapLayers, getMapLayersCoverage, getMapStyleMetadata } from "../../../shared/api/domain";
import { formatApiError } from "../../../shared/api/http";
import { getElectorateMap } from "../../../shared/api/qg";
import type { MapLayerItem } from "../../../shared/api/types";
import { useAutoLayerSwitch } from "../../../shared/hooks/useAutoLayerSwitch";
import { ChoroplethMiniMap } from "../../../shared/ui/ChoroplethMiniMap";

import { Panel } from "../../../shared/ui/Panel";
import { formatDecimal, formatLevelLabel, formatStatusLabel, formatTrendLabel, toNumber } from "../../../shared/ui/presentation";
import { StateBlock } from "../../../shared/ui/StateBlock";
import type { BasemapMode, VectorMapFeatureSelection, VizMode } from "../../../shared/ui/VectorMap";
import { useFilterStore } from "../../../shared/stores/filterStore";
import { emitTelemetry } from "../../../shared/observability/telemetry";

const TILE_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000/v1";
const BASEMAP_STREETS_URL =
  (import.meta.env.VITE_MAP_BASEMAP_STREETS_URL as string | undefined) ??
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const BASEMAP_LIGHT_URL =
  (import.meta.env.VITE_MAP_BASEMAP_LIGHT_URL as string | undefined) ??
  "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png";

const VIZ_MODES: { value: VizMode; label: string }[] = [
  { value: "choropleth", label: "Coropletico" },
  { value: "points", label: "Pontos" },
  { value: "heatmap", label: "Heatmap" },
  { value: "hotspots", label: "Hotspots" },
];

const BASEMAP_MODES: { value: BasemapMode; label: string }[] = [
  { value: "streets", label: "Ruas" },
  { value: "light", label: "Claro" },
  { value: "none", label: "Sem base" },
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

function normalizeBasemap(value: string | null): BasemapMode {
  const normalized = (value ?? "").trim().toLowerCase();
  if (normalized === "none" || normalized === "off" || normalized === "sem_base") {
    return "none";
  }
  if (normalized === "light" || normalized === "claro") {
    return "light";
  }
  return "streets";
}

function normalizeVizMode(value: string | null): VizMode {
  const normalized = (value ?? "").trim().toLowerCase();
  if (normalized === "points" || normalized === "heatmap" || normalized === "hotspots") {
    return normalized;
  }
  return "choropleth";
}

function normalizeRenderer(value: string | null) {
  const normalized = (value ?? "").trim().toLowerCase();
  if (normalized === "svg" || normalized === "fallback") {
    return false;
  }
  return true;
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
    return layer?.notes ?? "Camada hibrida com composicao de fontes oficiais e auxiliares.";
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
    return "Camada vetorial temporariamente indisponivel (503). O mapa continua ativo; tente novamente em instantes.";
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
  const initialMetric = searchParams.get("metric") || "MTE_NOVO_CAGED_SALDO_TOTAL";
  const initialPeriod = searchParams.get("period") || "2025";
  const initialLevel = normalizeMapLevel(searchParams.get("level"));
  const initialTerritoryId = searchParams.get("territory_id") || undefined;
  const initialLayerId = searchParams.get("layer_id") || null;
  const initialBasemap = normalizeBasemap(searchParams.get("basemap"));
  const initialVizMode = normalizeVizMode(searchParams.get("viz"));
  const initialUseVectorMap = normalizeRenderer(searchParams.get("renderer"));
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
  const [basemapMode, setBasemapMode] = useState<BasemapMode>(initialBasemap);
  const [useVectorMap, setUseVectorMap] = useState(initialUseVectorMap);
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
  const previousBasemapRef = useRef(initialBasemap);
  const previousLayerKeyRef = useRef<string>("");
  const previousElectoralLayerViewRef = useRef<ElectoralLayerView | null>(null);
  const previousMapOperationalStateRef = useRef<MapOperationalState | null>(null);
  const previousVectorErrorRef = useRef<string | null>(null);

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

  const electorateSectionQuery = useQuery({
    queryKey: ["qg", "map", "electorate-sections", appliedPeriod],
    queryFn: () =>
      getElectorateMap({
        level: "secao_eleitoral",
        year: resolveStrategicYear(appliedPeriod),
        metric: "voters",
        include_geometry: false,
        limit: 300,
      }),
    enabled: appliedMapScope === "territorial" && appliedLevel === "secao_eleitoral",
    staleTime: 60 * 1000,
  });
  const mapLayersError = mapLayersQuery.error ? formatApiError(mapLayersQuery.error) : null;
  const mapStyleError = mapStyleQuery.error ? formatApiError(mapStyleQuery.error) : null;
  const layersCoverageError = layersCoverageQuery.error ? formatApiError(layersCoverageQuery.error) : null;

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
        : appliedMapScope === "territorial" && !isChoroplethLevel && !useVectorMap
          ? "empty_simplified_unavailable"
          : appliedMapScope === "urban" && !useVectorMap
            ? "empty_svg_urban_unavailable"
            : "data";

  useEffect(() => {
    setVectorMapError(null);
    if (!canUseVectorMap) {
      setUseVectorMap(false);
    }
  }, [appliedLevel, appliedMetric, appliedPeriod, canUseVectorMap]);

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
      setLayerSelectionNotice("Camada detalhada anterior indisponivel para o nivel atual; selecao automatica restaurada.");
    }
  }, [appliedMapScope, availableLevelLayerIds, levelScopedLayers.length, selectedVectorLayerId]);

  useEffect(() => {
    if (appliedMapScope !== "territorial") {
      return;
    }
    if (previousAppliedLevelRef.current !== appliedLevel) {
      if (selectedVectorLayerId) {
        setLayerSelectionNotice("Nivel territorial alterado; camada detalhada reiniciada para recomendacao automatica.");
      }
      setSelectedVectorLayerId(null);
    }
    previousAppliedLevelRef.current = appliedLevel;
  }, [appliedLevel, appliedMapScope, selectedVectorLayerId]);

  useEffect(() => {
    const nextSearch = new URLSearchParams();
    nextSearch.set("metric", appliedMetric);
    nextSearch.set("period", appliedPeriod);
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
    if (!useVectorMap) {
      nextSearch.set("renderer", "svg");
    }

    const nextValue = nextSearch.toString();
    const currentValue = searchParams.toString();
    if (nextValue !== currentValue) {
      setSearchParams(nextSearch, { replace: true });
    }
  }, [
    appliedLevel,
    appliedMapScope,
    appliedMetric,
    appliedPeriod,
    appliedUrbanLayerId,
    basemapMode,
    currentZoom,
    searchParams,
    selectedTerritoryId,
    selectedVectorLayerId,
    setSearchParams,
    useVectorMap,
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
    if (previousBasemapRef.current === basemapMode) {
      return;
    }
    emitTelemetry({
      category: "lifecycle",
      name: "map_mode_changed",
      severity: "info",
      attributes: {
        basemap_mode: basemapMode,
        scope: appliedMapScope,
        level: appliedLevel,
      },
    });
    previousBasemapRef.current = basemapMode;
  }, [appliedLevel, appliedMapScope, basemapMode]);

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
        renderer: useVectorMap ? "advanced" : "simplified",
        metric: appliedMetric,
        period: appliedPeriod,
      },
    });
    previousMapOperationalStateRef.current = mapOperationalState;
  }, [appliedLevel, appliedMapScope, appliedMetric, appliedPeriod, mapOperationalState, useVectorMap]);

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
      setUseVectorMap(true);
      const nextZoom = Math.max(currentZoom, 14);
      setCurrentZoom(nextZoom);
      globalFilters.setZoom(nextZoom);
      setMapRecenterNotice("Preset aplicado: secoes eleitorais com foco no volume de eleitores por secao.");
      recenterMap(false);
      return;
    }

    setMapScope("urban");
    setUrbanLayerId("urban_pois");
    setAppliedMapScope("urban");
    setAppliedUrbanLayerId("urban_pois");
    setSelectedVectorLayerId(null);
    setUseVectorMap(true);
    setVizMode("points");
    setBasemapMode("light");
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
    setBasemapMode("streets");
    setVizMode("choropleth");
    setUseVectorMap(true);
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
      setExportError("Nao foi possivel localizar o mapa para exportacao. Use o modo simplificado.");
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
      setExportError("Nao foi possivel localizar o mapa para exportacao. Use o modo simplificado.");
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
          setExportError("Nao foi possivel preparar o canvas para exportacao.");
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
    return <StateBlock tone="loading" title="Carregando mapa" message="Consultando distribuicao territorial do indicador." />;
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
  const effectiveRendererLabel = useVectorMap && canUseVectorMap ? "Modo avancado" : "Modo simplificado";
  const effectiveBasemapLabel = BASEMAP_MODES.find((mode) => mode.value === basemapMode)?.label ?? basemapMode;
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
      ? "local_votacao: indisponivel no manifesto atual"
      : isPollingPlaceActive
        ? selectedPollingPlaceName
          ? `local_votacao: detectado (${selectedPollingPlaceName})`
          : "local_votacao: camada ativa sem nome detectado na feicao selecionada"
        : "local_votacao: disponivel (altere para Locais de votacao para detalhar o ponto)";
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
  const sectionElectorateTopItems = electorateSectionQuery.data
    ? [...electorateSectionQuery.data.items]
        .filter((item) => typeof item.value === "number")
        .sort((a, b) => (b.value ?? Number.NEGATIVE_INFINITY) - (a.value ?? Number.NEGATIVE_INFINITY))
        .slice(0, 5)
    : [];
  const hasSingleMunicipalityView =
    appliedMapScope === "territorial" && appliedLevel === "municipio" && sortedItems.length <= 1;

  const selectedTerritoryActions = appliedMapScope === "territorial" && selectedTerritoryIdSafe
    ? {
        profile: `/territorio/${encodeURIComponent(selectedTerritoryIdSafe)}`,
        priorities: `/prioridades?period=${encodeURIComponent(appliedPeriod)}&level=${encodeURIComponent(
          toPriorityLevel(appliedLevel),
        )}`,
        insights: `/insights?period=${encodeURIComponent(appliedPeriod)}`,
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

  return (
    <main className="page-grid">
      <Panel title="Mapa estrategico" subtitle="Distribuicao territorial por indicador e periodo">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            applyFilters();
          }}
        >
          <label>
            Escopo da camada
            <select value={mapScope} onChange={(event) => setMapScope(event.target.value as LayerScope)}>
              <option value="territorial">Territorial</option>
              <option value="urban">Urbana</option>
            </select>
          </label>
          {mapScope === "urban" ? (
            <label>
              Camada urbana
              <select value={urbanLayerId} onChange={(event) => setUrbanLayerId(event.target.value)}>
                {availableUrbanLayers.map((layerItem) => (
                  <option key={layerItem.id} value={layerItem.id}>
                    {layerItem.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <label>
            Indicador
            <input value={metric} onChange={(event) => setMetric(event.target.value)} placeholder="Ex: MTE_NOVO_CAGED_SALDO_TOTAL" />
          </label>
          <label>
            Periodo
            <input value={period} onChange={(event) => setPeriod(event.target.value)} />
          </label>
          {mapScope === "territorial" ? (
            <label>
              Nivel territorial
              <select value={level} onChange={(event) => setLevel(event.target.value)}>
                {availableFormLevels.length === 0 ? (
                  <option value="municipio">Municipio</option>
                ) : (
                  availableFormLevels.map((levelOption) => (
                    <option key={levelOption} value={levelOption}>
                      {formatLevelLabel(levelOption)}
                    </option>
                  ))
                )}
              </select>
            </label>
          ) : null}
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>
        <div className="filter-actions" aria-label="Presets estrategicos do mapa">
          <button type="button" className="button-secondary" onClick={() => applyStrategicPreset("electoral_sections")}>
            Eleitorado por secao
          </button>
          <button type="button" className="button-secondary" onClick={() => applyStrategicPreset("urban_services")}>
            Servicos por bairros
          </button>
        </div>
        {hasSingleMunicipalityView ? (
          <p className="map-layer-guidance">
            Recorte municipal unico limita a decisao estrategica. Use os presets para abrir leitura por secoes eleitorais
            ou distribuicao de servicos urbanos por bairro.
          </p>
        ) : null}
        <p className="map-selected-note">
          {recommendedLayer ? (
            <>
              Camada recomendada: {recommendedLayer.label} ({formatZoomRange(recommendedLayer.zoom_min, recommendedLayer.zoom_max)}) | classificacao:{" "}
              {recommendedLayerClassification}
            </>
          ) : (
            "Camada recomendada: manifesto de camadas em carregamento."
          )}
          {autoLayer && autoLayer.id !== recommendedLayer?.id
            ? ` | Auto-zoom: ${autoLayer.label} (${formatLayerClassificationLabel(autoLayer)}; z=${currentZoom})`
            : null}
        </p>
        <p className="map-selected-note" aria-label="Resumo operacional do mapa">
          Resumo do mapa: escopo {formatScopeLabel(appliedMapScope)} | nivel {formatLevelLabel(appliedLevel)} | camada {effectiveLayer?.label ?? "n/d"} | visualizacao {effectiveVizLabel} | base {effectiveBasemapLabel} | renderizacao {effectiveRendererLabel}
        </p>
        {appliedMapScope === "territorial" && isChoroplethLevel && sortedItems.length > 0 ? (
          <section className="map-context-card" aria-label="Leitura executiva imediata">
            <h3>Leitura executiva imediata</h3>
            <p>
              Prioridade territorial atual: <strong>{topTerritory?.territory_name ?? "n/d"}</strong>
              {topTerritory ? ` (${formatNumber(topTerritory.value)})` : ""}.
            </p>
            {bottomTerritory ? (
              <p>
                Menor valor no recorte: <strong>{bottomTerritory.territory_name}</strong>
                {` (${formatNumber(bottomTerritory.value)})`}.
              </p>
            ) : null}
            {selectedItem && selectedTerritoryRank ? (
              <p>
                Território selecionado: <strong>{selectedItem.territory_name}</strong>
                {` | posição ${selectedTerritoryRank}/${sortedItems.length}`}.
              </p>
            ) : (
              <p>Próximo passo: selecione um território para abrir ações contextuais de prioridade, insights e brief.</p>
            )}
          </section>
        ) : null}
        {hasMultipleLevelLayers ? (
          <div className="map-layer-toggle">
            <label>
              {isElectoralSectionLevel ? "Camada eleitoral detalhada" : "Camada detalhada"}
              <select
                value={selectedVectorLayerId ?? ""}
                onChange={(event) => {
                  setLayerSelectionNotice(null);
                  setSelectedVectorLayerId(event.target.value || null);
                }}
                aria-label={isElectoralSectionLevel ? "Camada eleitoral detalhada" : "Camada detalhada"}
              >
                <option value="">Automatica (recomendada no zoom atual)</option>
                {levelScopedLayers.map((layerItem) => (
                  <option key={layerItem.id} value={layerItem.id}>
                    {layerItem.label}
                  </option>
                ))}
              </select>
            </label>
            <p
              className="map-selected-note"
              title={effectiveLayerHint}
            >
              Camada ativa: <strong>{effectiveLayer?.label ?? "n/d"}</strong>
              {effectiveLayer ? ` | classificacao: ${effectiveLayerClassification}` : ""}
              {effectiveLayer ? ` | origem: ${effectiveLayerSourceLabel}` : ""}
              {effectiveLayer?.proxy_method ? ` | metodo: ${effectiveLayer.proxy_method}` : ""}
            </p>
            {selectedVectorLayerId ? (
              <button
                type="button"
                className="button-secondary"
                onClick={() => {
                  setLayerSelectionNotice("Selecao automatica restaurada manualmente.");
                  setSelectedVectorLayerId(null);
                }}
                aria-label="Usar camada automatica"
              >
                Usar camada automatica
              </button>
            ) : null}
          </div>
        ) : null}
        {layerSelectionNotice ? <p className="map-layer-guidance">{layerSelectionNotice}</p> : null}
        {isElectoralSectionLevel && hasPollingPlaceLayer ? (
          <div className="map-layer-guidance">
            <p>
              {isPollingPlaceActive
                ? "Local de votacao ativo: pontos derivados de secao eleitoral com nome detectado no payload oficial."
                : "Dica: selecione 'Locais de votacao' para ver o campo local_votacao quando disponivel."}
              {sectionGeometryLayer ? ` Camada de referencia territorial: ${sectionGeometryLayer.label}.` : ""}
            </p>
            {canTogglePollingLayer ? (
              <button
                type="button"
                className="button-secondary"
                onClick={() => {
                  setLayerSelectionNotice(null);
                  setSelectedVectorLayerId(pollingLayerToggleTargetId);
                }}
                aria-label={isPollingPlaceActive ? "Exibir secoes eleitorais" : "Exibir locais de votacao"}
              >
                {isPollingPlaceActive ? "Exibir secoes eleitorais" : "Exibir locais de votacao"}
              </button>
            ) : null}
          </div>
        ) : null}
        {isElectoralSectionLevel && !hasPollingPlaceLayer ? (
          <p className="map-layer-guidance">
            Camada local_votacao indisponivel no manifesto atual; mantendo exibicao por secao eleitoral.
            {sectionGeometryLayer ? ` Camada ativa de referencia: ${sectionGeometryLayer.label}.` : ""}
          </p>
        ) : null}
        {isElectoralSectionLevel ? (
          <div className="map-inline-legend" aria-label="Legenda eleitoral executiva">
            <h4>Legenda eleitoral</h4>
            <ul>
              <li>
                <span className="map-legend-swatch map-legend-swatch-section" aria-hidden="true" />
                <span>Secoes eleitorais (recorte territorial)</span>
              </li>
              <li>
                <span className="map-legend-swatch map-legend-swatch-polling" aria-hidden="true" />
                <span>Locais de votacao (pontos de atendimento)</span>
              </li>
            </ul>
            <p className="map-selected-note" title="Secoes eleitorais representam os recortes territoriais; locais de votacao representam os pontos detectados no payload quando disponivel.">
              Círculos priorizam leitura proporcional do eleitorado no zoom atual.
            </p>
          </div>
        ) : null}
        {isElectoralSectionLevel ? (
          electorateSectionQuery.isPending ? (
            <StateBlock
              tone="loading"
              title="Carregando eleitorado por secao"
              message="Consultando volume de eleitores para apoiar a leitura territorial fina."
            />
          ) : electorateSectionQuery.error ? (
            <StateBlock
              tone="error"
              title="Falha ao carregar eleitorado por secao"
              message={formatApiError(electorateSectionQuery.error).message}
              requestId={formatApiError(electorateSectionQuery.error).requestId}
              onRetry={() => void electorateSectionQuery.refetch()}
            />
          ) : sectionElectorateTopItems.length > 0 ? (
            <section className="map-context-card" aria-label="Top secoes por eleitorado">
              <h3>Top secoes por eleitorado</h3>
              <p>Referencia: {electorateSectionQuery.data?.year ?? "n/d"} | metrica: eleitores.</p>
              <div className="table-wrap">
                <table aria-label="Top secoes por eleitores">
                  <thead>
                    <tr>
                      <th>Secao</th>
                      <th>Eleitores</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sectionElectorateTopItems.map((item) => (
                      <tr key={`${item.territory_id}-${item.year}`}>
                        <td>{item.territory_name}</td>
                        <td>{formatNumber(item.value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : (
            <StateBlock
              tone="empty"
              title="Sem eleitorado por secao"
              message="Nao ha volume de eleitores por secao para o periodo selecionado."
            />
          )
        ) : null}
        {pollingPlaceAvailabilityNote ? <p className="map-selected-note">{pollingPlaceAvailabilityNote}</p> : null}
        <div className="zoom-control compact" aria-label="Controle de zoom">
          <label>
            Zoom
            <input
              type="range"
              min={contextualZoomFloor}
              max={18}
              step={1}
              value={currentZoom}
              onChange={(e) => handleZoomChange(Number(e.target.value))}
              aria-label="Nivel de zoom do mapa"
            />
            <span className="zoom-value">{currentZoom}</span>
          </label>
        </div>
        <p className="map-selected-note">Zoom contextual minimo recomendado: z{contextualZoomFloor}.</p>
        {mapRecenterNotice ? <p className="map-selected-note">{mapRecenterNotice}</p> : null}
        {appliedMapScope === "territorial" && isChoroplethLevel ? (
          <div className="map-territory-search">
            <label htmlFor="territory-search-input">Buscar territorio</label>
            <div className="map-territory-search-row">
              <input
                id="territory-search-input"
                list="territory-search-options"
                value={territorySearch}
                onChange={(event) => setTerritorySearch(event.target.value)}
                placeholder="Digite o nome do territorio"
              />
              <button type="button" className="button-secondary" onClick={focusTerritoryFromSearch} disabled={sortedItems.length === 0}>
                Focar territorio
              </button>
              <button type="button" className="button-secondary" onClick={focusSelectedTerritory} disabled={!selectedTerritoryId}>
                Focar selecionado
              </button>
              <button type="button" className="button-secondary" onClick={() => recenterMap()}>
                Recentrar mapa
              </button>
            </div>
            <datalist id="territory-search-options">
              {sortedItems.map((item) => (
                <option key={item.territory_id} value={item.territory_name} />
              ))}
            </datalist>
            {territoryFocusNotice ? <p className="map-selected-note">{territoryFocusNotice}</p> : null}
          </div>
        ) : appliedMapScope === "territorial" ? (
          <p className="map-selected-note">
            Busca e foco territorial detalhado estao disponiveis no recorte coropletico (municipio/distrito). Para
            niveis granulares, mantenha o modo avancado para exploracao operacional.
          </p>
        ) : (
          <div className="map-territory-search-row">
            <button type="button" className="button-secondary" onClick={focusSelectedTerritory} disabled={!selectedTerritoryId}>
              Focar selecionado
            </button>
            <button type="button" className="button-secondary" onClick={() => recenterMap()}>
              Recentrar mapa
            </button>
            {territoryFocusNotice ? <p className="map-selected-note">{territoryFocusNotice}</p> : null}
          </div>
        )}
        {mapLayersQuery.isPending && !mapLayersQuery.data ? (
          <StateBlock
            tone="loading"
            title="Carregando manifesto de camadas"
            message="Buscando catalogo territorial e urbano para configuracao do mapa."
          />
        ) : mapLayersError ? (
          <StateBlock
            tone="error"
            title="Manifesto de camadas indisponivel"
            message={`${mapLayersError.message} ${
              appliedMapScope === "territorial"
                ? `Mantendo fallback em ${choroplethParams.level}.`
                : "Mantendo camadas urbanas de contingencia."
            }`}
            requestId={mapLayersError.requestId}
            onRetry={() => void mapLayersQuery.refetch()}
          />
        ) : null}
        {layersCoverageQuery.isPending && !layersCoverageQuery.data ? (
          <StateBlock
            tone="loading"
            title="Carregando cobertura da camada"
            message="Conferindo geometrias e disponibilidade de indicador no recorte aplicado."
          />
        ) : layersCoverageError ? (
          <StateBlock
            tone="error"
            title="Falha ao carregar cobertura da camada"
            message={layersCoverageError.message}
            requestId={layersCoverageError.requestId}
            onRetry={() => void layersCoverageQuery.refetch()}
          />
        ) : selectedLayerCoverage ? (
          <p className="map-selected-note">
            Cobertura da camada: {selectedLayerCoverage.territories_with_geometry}/{selectedLayerCoverage.territories_total} com
            geometria
            {isChoroplethLevel
              ? ` | ${selectedLayerCoverage.territories_with_indicator} com indicador no recorte`
              : ""}
            {selectedLayerCoverage.notes ? ` | ${selectedLayerCoverage.notes}` : ""}
          </p>
        ) : appliedMapScope === "urban" ? (
          <p className="map-selected-note">
            Cobertura urbana ativa em camadas operacionais (`map.urban_road_segment` e `map.urban_poi`).
          </p>
        ) : null}
      </Panel>

      <Panel title="Mapa visual" subtitle="Visualizacao vetorial MVT com fallback SVG">
        <div className="map-toolbar">
          <div className="map-toolbar-block">
            <p className="map-toolbar-label">Modo de visualizacao</p>
            <div className="viz-mode-selector" role="radiogroup" aria-label="Modo de visualizacao">
              {VIZ_MODES.map((mode) => (
                <button
                  key={mode.value}
                  type="button"
                  className={`viz-mode-btn${vizMode === mode.value ? " viz-mode-active" : ""}`}
                  onClick={() => setVizMode(mode.value)}
                  role="radio"
                  aria-checked={vizMode === mode.value}
                >
                  {mode.label}
                </button>
              ))}
            </div>
          </div>
          <div className="map-toolbar-block">
            <p className="map-toolbar-label">Mapa base</p>
            <div className="viz-mode-selector" role="radiogroup" aria-label="Mapa base">
              {BASEMAP_MODES.map((mode) => (
                <button
                  key={mode.value}
                  type="button"
                  className={`viz-mode-btn${basemapMode === mode.value ? " viz-mode-active" : ""}`}
                  onClick={() => setBasemapMode(mode.value)}
                  role="radio"
                  aria-checked={basemapMode === mode.value}
                >
                  {mode.label}
                </button>
              ))}
            </div>
          </div>
          <div className="map-toolbar-block">
            <p className="map-toolbar-label">Modo de exibicao</p>
            <button
              type="button"
              className="button-secondary"
              onClick={() => setUseVectorMap((prev) => !prev)}
              disabled={!canUseVectorMap}
              aria-label={useVectorMap ? "Alternar para modo simplificado" : "Alternar para modo avancado"}
            >
              {useVectorMap ? "Modo simplificado" : canUseVectorMap ? "Modo avancado" : "Somente simplificado"}
            </button>
          </div>
        </div>
        <div className="panel-actions-row">
          <button type="button" className="button-secondary" onClick={exportMapSvg} aria-label="Exportar mapa como SVG">
            Exportar SVG
          </button>
          <button type="button" className="button-secondary" onClick={exportMapPng} aria-label="Exportar mapa como PNG">
            Exportar PNG
          </button>
        </div>
        {mapStyleQuery.data ? (
          <div className="map-style-meta">
            <p>
              Modo: <strong>{VIZ_MODES.find((mode) => mode.value === effectiveVizMode)?.label ?? effectiveVizMode}</strong> | versao: {mapStyleQuery.data.version}
            </p>
            <div className="map-style-chip-row">
              {mapStyleQuery.data.severity_palette.map((item) => (
                <span key={item.severity} className="map-style-chip" style={{ borderColor: item.color, color: item.color }}>
                  {item.label}
                </span>
              ))}
              <span className="map-style-chip" style={{ borderColor: "#9ca3af", color: "#6b7280" }}>
                Sem dado
              </span>
            </div>
            {effectiveLayer ? (
              <p title={effectiveLayerHint}>
                Classificacao da camada: <strong>{effectiveLayerClassification}</strong>
                {effectiveLayer?.proxy_method ? " | metodo proxy disponivel no tooltip." : ""}
              </p>
            ) : null}
            {isPollingPlaceActive ? (
              <p>Camada local_votacao: o tooltip e a selecao priorizam o nome do local de votacao detectado.</p>
            ) : null}
            {effectiveLayer?.layer_kind === "point" ? (
              <p>Camada atual e pontual; coropletico muda automaticamente para pontos.</p>
            ) : null}
          </div>
        ) : null}
        {mapStyleQuery.isPending && !mapStyleQuery.data ? (
          <StateBlock
            tone="loading"
            title="Carregando metadados de estilo"
            message="Preparando paleta, severidade e faixas para legenda do mapa."
          />
        ) : mapStyleError ? (
          <StateBlock
            tone="error"
            title="Falha ao carregar metadados de estilo"
            message={`${mapStyleError.message} Legenda padrao mantida.`}
            requestId={mapStyleError.requestId}
            onRetry={() => void mapStyleQuery.refetch()}
          />
        ) : null}
        {useVectorMap && canUseVectorMap ? (
          <div className="map-canvas-shell">
            <Suspense
              fallback={
                <StateBlock
                  tone="loading"
                  title="Carregando mapa avancado"
                  message="Preparando camadas vetoriais e base cartografica."
                />
              }
            >
              <LazyVectorMap
                tileBaseUrl={TILE_BASE_URL}
                metric={appliedMetric}
                period={appliedPeriod}
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
                  light: BASEMAP_LIGHT_URL,
                }}
              />
            </Suspense>
          </div>
        ) : appliedMapScope === "territorial" && isChoroplethLevel ? (
          <ChoroplethMiniMap
            items={sortedItems.map((item) => ({
              territoryId: item.territory_id,
              territoryName: item.territory_name,
              value: item.value,
              geometry: item.geometry,
            }))}
            selectedTerritoryId={selectedTerritoryId}
            onSelect={(territoryId) => {
              setSelectedTerritoryId(territoryId);
              const selected = sortedItems.find((item) => item.territory_id === territoryId);
              if (selected) {
                setTerritorySearch(selected.territory_name);
              }
              setSelectedFeature(null);
            }}
          />
        ) : appliedMapScope === "territorial" ? (
          <StateBlock
            tone="empty"
            title="Modo simplificado indisponivel neste nivel"
            message="Niveis granulares (setor/zona/secao) exigem modo avancado para leitura espacial consistente."
          />
        ) : (
          <StateBlock
            tone="empty"
            title="Modo SVG indisponivel para camadas urbanas"
            message="Reative o modo avancado para explorar viario e pontos de interesse."
          />
        )}
        {drawerTerritoryName ? (
          <p className="map-selected-note">
            Selecionado: <strong>{selectedFeatureLabel ?? drawerTerritoryName}</strong> | valor: {drawerScoreDisplay}
            {selectedFeatureCategory ? <> | categoria: {selectedFeatureCategory}</> : null}
            {territoryPanelCollapsed ? (
              <button
                type="button"
                className="inline-link-button"
                onClick={() => setTerritoryPanelCollapsed(false)}
                aria-label="Expandir painel territorial"
              >
                Expandir detalhes
              </button>
            ) : null}
          </p>
        ) : null}
        {vectorMapError ? <p className="map-export-error">{vectorMapError}</p> : null}
        {exportError ? <p className="map-export-error">{exportError}</p> : null}
      </Panel>

      <Panel title="Ranking territorial" subtitle="Leitura tabular do choropleth para apoio a priorizacao">
        <div className="panel-actions-row">
          <button
            type="button"
            className="button-secondary"
            onClick={exportCsv}
            disabled={sortedItems.length === 0}
            aria-label="Exportar ranking como CSV"
          >
            Exportar CSV
          </button>
        </div>
        {appliedMapScope === "urban" ? (
          <StateBlock
            tone="empty"
            title="Ranking indisponivel para camada urbana"
            message="Use o modo avancado para explorar viario e pontos de interesse. O ranking tabular permanece no escopo territorial."
          />
        ) : !isChoroplethLevel ? (
          <StateBlock
            tone="empty"
            title="Ranking indisponivel neste nivel"
            message="O ranking tabular ainda usa o endpoint de choropleth (municipio/distrito). O modo avancado continua ativo para exploracao."
          />
        ) : sortedItems.length === 0 ? (
          <StateBlock tone="empty" title="Sem dados para mapa" message="Nenhum territorio encontrado para o recorte informado." />
        ) : (
          <div className="table-wrap">
            <table aria-label="Ranking territorial">
              <thead>
                <tr>
                  <th>Territorio</th>
                  <th>Nivel</th>
                  <th>Periodo</th>
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
      </Panel>

      {drawerTerritoryName && !territoryPanelCollapsed ? (
        <Panel
          title={drawerTerritoryName}
          subtitle={`${formatLevelLabel(appliedLevel)} · ${drawerStatusDisplay} · Tendencia: ${drawerTrendDisplay}`}
        >
          <div className="territory-detail-bar">
            <button
              type="button"
              className="button-secondary territory-detail-close"
              onClick={() => {
                setTerritoryPanelCollapsed(true);
                setSelectedFeature(null);
                setSelectedTerritoryId(undefined);
              }}
              aria-label="Fechar painel territorial"
            >
              ✕ Fechar
            </button>
          </div>

          <div className="territory-detail-grid">
            <div className="territory-detail-score-card">
              <p>Valor selecionado</p>
              <strong>{drawerScoreDisplay} (selecao)</strong>
            </div>

            <div className="territory-detail-stats" role="list" aria-label="Metricas rapidas do territorio">
              <article role="listitem">
                <span>Periodo</span>
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
              <article role="listitem">
                <span>Cobertura</span>
                <strong>{drawerCoverageDisplay}</strong>
              </article>
            </div>
          </div>

          <section>
            <h3 className="territory-detail-section-title">Evidencias</h3>
            {drawerEvidenceItems.length > 0 ? (
              <ul className="territory-detail-evidence-list">
                {drawerEvidenceItems.map(([key, value]) => (
                  <li key={key}>
                    <strong>{key}:</strong> {String(value)}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="territory-detail-meta-line">Nenhuma evidencia adicional disponivel para esta selecao.</p>
            )}
          </section>

          {selectedTerritoryActions ? (
            <nav className="territory-detail-actions" aria-label="Acoes territoriais">
              <Link className="button-secondary" to={selectedTerritoryActions.profile}>
                Abrir perfil selecionado
              </Link>
              <Link className="button-secondary" to={selectedTerritoryActions.priorities}>
                Abrir prioridades do territorio
              </Link>
              <Link className="button-secondary" to={selectedTerritoryActions.insights}>
                Ver insights deste recorte
              </Link>
              <Link className="button-secondary" to={selectedTerritoryActions.briefs}>
                Abrir brief do territorio
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
                  Geocodificar selecao
                </a>
              ) : null}
              {selectedUrbanActions.nearbyPois ? (
                <a className="button-secondary" href={selectedUrbanActions.nearbyPois} target="_blank" rel="noreferrer">
                  Buscar POIs proximos
                </a>
              ) : null}
            </nav>
          ) : null}

          <details className="territory-detail-meta-details">
            <summary>Contexto operacional</summary>
            <div className="territory-detail-meta-grid" aria-label="Contexto operacional da camada">
              <p className="territory-detail-meta-line">
                <strong>Fonte:</strong> {selectedFeatureSource ?? effectiveLayer?.source ?? "n/d"}
              </p>
              <p className="territory-detail-meta-line">
                <strong>Classificacao:</strong> {effectiveLayerClassification}
              </p>
              <p className="territory-detail-meta-line">
                <strong>Renderizacao:</strong> {effectiveRendererLabel}
              </p>
              <p className="territory-detail-meta-line">
                <strong>Base:</strong> {effectiveBasemapLabel}
              </p>
              <p className="territory-detail-meta-line">
                <strong>Modo:</strong> {effectiveVizLabel}
              </p>
              {drawerTerritoryId ? (
                <p className="territory-detail-meta-line">
                  <strong>Territorio ID:</strong> {drawerTerritoryId}
                </p>
              ) : null}
              {isPollingPlaceActive ? (
                <p className="territory-detail-meta-line">
                  <strong>Local votacao:</strong>{" "}
                  {selectedPollingPlaceName ?? "indisponivel no payload da feicao selecionada"}
                </p>
              ) : null}
              {selectedFeatureSubcategory ? (
                <p className="territory-detail-meta-line">
                  <strong>Subcategoria:</strong> {selectedFeatureSubcategory}
                </p>
              ) : null}
            </div>
          </details>
        </Panel>
      ) : null}
    </main>
  );
}
