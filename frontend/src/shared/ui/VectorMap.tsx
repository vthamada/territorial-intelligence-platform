import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { MapLayerItem } from "../api/types";
import { resolveLayerForZoom } from "../hooks/useAutoLayerSwitch";

export type VizMode = "choropleth" | "points" | "heatmap" | "critical" | "gap";
export type BasemapMode = "none" | "streets" | "light";

type TooltipContext = {
  indicatorName?: string;
  trend?: string | null;
  source?: string;
  updatedAt?: string | null;
};

export type VectorMapFeatureSelection = {
  tid: string;
  tname: string;
  val?: number;
  label?: string;
  category?: string;
  lon?: number;
  lat?: number;
  layerKind?: MapLayerItem["layer_kind"];
  rawProperties?: Record<string, unknown>;
  overlayId?: string;
};

type BasemapTileUrls = {
  streets?: string;
  light?: string;
};

export type OverlayLayerConfig = {
  /** Unique identifier for the overlay */
  id: string;
  /** Label for tooltip display */
  label: string;
  /** Layer ID used to build the tile URL (e.g. "urban_pois") */
  tileLayerId: string;
  /** How to render: circle points, fill polygons, or heatmap */
  vizType: "circle" | "fill" | "heatmap";
  /** Primary color for the overlay */
  color: string;
  /** Optional MapLibre filter expression applied client-side */
  filter?: maplibregl.ExpressionSpecification;
  /** Whether this overlay is currently visible */
  enabled: boolean;
  /** Opacity (0..1) */
  opacity?: number;
  /** Min zoom to show this overlay */
  minZoom?: number;
};

/** GeoJSON source with MapLibre native clustering for proportional circles */
export type GeoJsonClusterConfig = {
  /** Unique identifier for this GeoJSON layer */
  id: string;
  /** GeoJSON FeatureCollection data */
  data: GeoJSON.FeatureCollection;
  /** Primary color for unclustered points and clusters */
  color: string;
  /** Opacity for unclustered points (0..1) */
  opacity?: number;
  /** Stroke color for points */
  strokeColor?: string;
  /** Stroke width for points */
  strokeWidth?: number;
  /** MapLibre expression for unclustered point radius (proportional sizing) */
  radiusExpression?: maplibregl.ExpressionSpecification | number;
  /** Cluster radius in pixels (default: 50) */
  clusterRadius?: number;
  /** Max zoom for clustering (default: 14) */
  clusterMaxZoom?: number;
  /** Cluster aggregation properties */
  clusterProperties?: Record<string, unknown>;
  /** Expression for cluster label text */
  clusterLabelExpression?: maplibregl.ExpressionSpecification;
  /** Function to build tooltip HTML for unclustered points */
  tooltipFn?: (props: Record<string, unknown>) => string;
  /** Function to build tooltip HTML for cluster points */
  clusterTooltipFn?: (props: Record<string, unknown>) => string;
  /** Min zoom to show this layer */
  minZoom?: number;
  /** Whether this layer is currently enabled */
  enabled?: boolean;
};

export type VectorMapProps = {
  tileBaseUrl: string;
  layers?: MapLayerItem[];
  defaultLayerId?: string;
  vizMode?: VizMode;
  center?: [number, number];
  zoom?: number;
  onFeatureClick?: (feature: VectorMapFeatureSelection) => void;
  onZoomChange?: (zoom: number) => void;
  onError?: (message: string) => void;
  colorStops?: Array<{ value: number; color: string }>;
  selectedTerritoryId?: string;
  basemapMode?: BasemapMode;
  basemapTileUrls?: BasemapTileUrls;
  resetViewSignal?: number;
  focusTerritorySignal?: number;
  showContextLabels?: boolean;
  tooltipContext?: TooltipContext;
  overlays?: OverlayLayerConfig[];
  /** GeoJSON cluster layers (e.g. proportional electoral section circles) */
  geoJsonLayers?: GeoJsonClusterConfig[];
  /** Render primary MVT layer as contour only (line, no fill) */
  boundaryOnly?: boolean;
};

const DEFAULT_CENTER: [number, number] = [-43.62, -18.09];
const DEFAULT_ZOOM = 4;
const BASEMAP_SOURCE_ID = "basemap-source";
const BASEMAP_LAYER_ID = "basemap-layer";
const SOURCE_ID = "mvt-source";
const INTERACTION_LAYER_IDS = ["fill-layer", "points-layer"] as const;
const DEFAULT_BASEMAP_TILE_URLS: Required<BasemapTileUrls> = {
  streets: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  light: "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
};

const DEFAULT_COLOR_STOPS: Array<{ value: number; color: string }> = [
  { value: 0, color: "#dbeafe" },
  { value: 20, color: "#93c5fd" },
  { value: 40, color: "#60a5fa" },
  { value: 70, color: "#3b82f6" },
  { value: 85, color: "#1d4ed8" },
];

function buildValueExpression(): maplibregl.ExpressionSpecification {
  return ["coalesce", ["get", "val"], ["get", "value"]] as maplibregl.ExpressionSpecification;
}

function buildNumericValueExpression(): maplibregl.ExpressionSpecification {
  return ["to-number", buildValueExpression(), -1] as maplibregl.ExpressionSpecification;
}

function buildHasValueFilter(): maplibregl.ExpressionSpecification {
  const valueExpression = buildValueExpression();
  return ["all", ["!=", valueExpression, null], ["!=", valueExpression, ""]] as maplibregl.ExpressionSpecification;
}

function buildLabelFieldExpression(): maplibregl.ExpressionSpecification {
  return [
    "coalesce",
    ["get", "label"],
    ["get", "name"],
    ["get", "tname"],
    ["get", "territory_name"],
    ["get", "road_name"],
    ["get", "poi_name"],
    ["get", "category"],
    "",
  ] as maplibregl.ExpressionSpecification;
}

function buildHasLabelFilter(): maplibregl.ExpressionSpecification {
  const labelExpression = buildLabelFieldExpression();
  return ["all", ["!=", labelExpression, null], ["!=", labelExpression, ""]] as maplibregl.ExpressionSpecification;
}

function buildTileUrl(baseUrl: string, layerId: string): string {
  return `${baseUrl}/map/tiles/${layerId}/{z}/{x}/{y}.mvt`;
}

function buildFillColor(stops: Array<{ value: number; color: string }>): maplibregl.ExpressionSpecification {
  const interpolationExpression: unknown[] = ["interpolate", ["linear"], buildNumericValueExpression()];
  for (const stop of stops) {
    interpolationExpression.push(stop.value);
    interpolationExpression.push(stop.color);
  }
  const interpolation = interpolationExpression as maplibregl.ExpressionSpecification;
  return ["case", buildHasValueFilter(), interpolation, "#d1d5db"] as unknown as maplibregl.ExpressionSpecification;
}

function resolveBasemapTileUrl(mode: BasemapMode, urls?: BasemapTileUrls): string | null {
  if (mode === "none") {
    return null;
  }
  const merged = {
    ...DEFAULT_BASEMAP_TILE_URLS,
    ...(urls ?? {}),
  };
  return mode === "light" ? merged.light : merged.streets;
}

function resolveBasemapAttribution(mode: BasemapMode): string | undefined {
  if (mode === "none") {
    return undefined;
  }
  if (mode === "light") {
    return "(c) OpenStreetMap contributors (c) CARTO";
  }
  return "(c) OpenStreetMap contributors";
}

function resolvePolygonFillOpacity(mode: BasemapMode): number {
  if (mode === "none") {
    return 0.75;
  }
  if (mode === "light") {
    return 0.42;
  }
  return 0.34;
}

function resolveBoundaryPaint(mode: BasemapMode): { color: string; width: number } {
  if (mode === "none") {
    return { color: "#6b7280", width: 0.5 };
  }
  if (mode === "light") {
    return { color: "rgba(15, 23, 42, 0.55)", width: 0.9 };
  }
  return { color: "rgba(15, 23, 42, 0.65)", width: 1.1 };
}

function safeEaseTo(map: maplibregl.Map, options: { center?: [number, number]; zoom?: number; duration?: number; essential?: boolean }) {
  const maybeMap = map as maplibregl.Map & {
    easeTo?: (next: { center?: [number, number]; zoom?: number; duration?: number; essential?: boolean }) => void;
    setCenter?: (center: [number, number]) => void;
    setZoom?: (zoom: number) => void;
  };
  if (typeof maybeMap.easeTo === "function") {
    maybeMap.easeTo(options);
    return;
  }
  if (options.center && typeof maybeMap.setCenter === "function") {
    maybeMap.setCenter(options.center);
  }
  if (typeof options.zoom === "number" && typeof maybeMap.setZoom === "function") {
    maybeMap.setZoom(options.zoom);
  }
}

function safeFitBounds(map: maplibregl.Map, bounds: [[number, number], [number, number]]) {
  const maybeMap = map as maplibregl.Map & {
    fitBounds?: (nextBounds: [[number, number], [number, number]], options: { padding: number; maxZoom: number; duration: number; essential: boolean }) => void;
    setCenter?: (center: [number, number]) => void;
  };
  if (typeof maybeMap.fitBounds === "function") {
    maybeMap.fitBounds(bounds, {
      padding: 40,
      maxZoom: 15,
      duration: 600,
      essential: true,
    });
    return;
  }
  if (typeof maybeMap.setCenter === "function") {
    const center: [number, number] = [
      (bounds[0][0] + bounds[1][0]) / 2,
      (bounds[0][1] + bounds[1][1]) / 2,
    ];
    maybeMap.setCenter(center);
  }
}

function collectLngLatPairs(coordinates: unknown, target: Array<[number, number]>) {
  if (!Array.isArray(coordinates)) {
    return;
  }
  if (
    coordinates.length >= 2 &&
    typeof coordinates[0] === "number" &&
    typeof coordinates[1] === "number"
  ) {
    target.push([coordinates[0], coordinates[1]]);
    return;
  }
  for (const item of coordinates) {
    collectLngLatPairs(item, target);
  }
}

function buildBoundsFromGeometry(
  geometry: maplibregl.MapGeoJSONFeature["geometry"],
): maplibregl.LngLatBoundsLike | null {
  const pairs: Array<[number, number]> = [];
  if (geometry.type === "GeometryCollection") {
    for (const childGeometry of geometry.geometries) {
      const childBounds = buildBoundsFromGeometry(childGeometry);
      if (!childBounds) {
        continue;
      }
      const [childSw, childNe] = childBounds as [[number, number], [number, number]];
      pairs.push(childSw, childNe);
    }
  } else {
    collectLngLatPairs(geometry.coordinates, pairs);
  }
  if (pairs.length === 0) {
    return null;
  }
  let minLng = Number.POSITIVE_INFINITY;
  let minLat = Number.POSITIVE_INFINITY;
  let maxLng = Number.NEGATIVE_INFINITY;
  let maxLat = Number.NEGATIVE_INFINITY;
  for (const [lng, lat] of pairs) {
    if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
      continue;
    }
    minLng = Math.min(minLng, lng);
    minLat = Math.min(minLat, lat);
    maxLng = Math.max(maxLng, lng);
    maxLat = Math.max(maxLat, lat);
  }
  if (!Number.isFinite(minLng) || !Number.isFinite(minLat) || !Number.isFinite(maxLng) || !Number.isFinite(maxLat)) {
    return null;
  }
  return [
    [minLng, minLat],
    [maxLng, maxLat],
  ];
}

export function VectorMap({
  tileBaseUrl,
  layers,
  defaultLayerId,
  vizMode = "choropleth",
  center = DEFAULT_CENTER,
  zoom = DEFAULT_ZOOM,
  onFeatureClick,
  onZoomChange,
  onError,
  colorStops = DEFAULT_COLOR_STOPS,
  selectedTerritoryId,
  basemapMode = "streets",
  basemapTileUrls,
  resetViewSignal = 0,
  focusTerritorySignal = 0,
  showContextLabels = true,
  tooltipContext,
  overlays,
  geoJsonLayers,
  boundaryOnly = false,
}: VectorMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [currentLayerId, setCurrentLayerId] = useState<string | undefined>(undefined);

  const interactionLayerRef = useRef<string | null>(null);
  const clickHandlerRef = useRef<((event: maplibregl.MapLayerMouseEvent) => void) | null>(null);
  const enterHandlerRef = useRef<(() => void) | null>(null);
  const leaveHandlerRef = useRef<(() => void) | null>(null);
  const moveHandlerRef = useRef<((event: maplibregl.MapLayerMouseEvent) => void) | null>(null);
  const hoverPopupRef = useRef<maplibregl.Popup | null>(null);
  const overlayInteractionLayersRef = useRef<string[]>([]);
  const overlayClickHandlersRef = useRef<Map<string, (event: maplibregl.MapLayerMouseEvent) => void>>(new Map());
  const overlayEnterHandlersRef = useRef<Map<string, () => void>>(new Map());
  const overlayLeaveHandlersRef = useRef<Map<string, () => void>>(new Map());
  const overlayMoveHandlersRef = useRef<Map<string, (event: maplibregl.MapLayerMouseEvent) => void>>(new Map());
  const geoJsonInteractionLayersRef = useRef<string[]>([]);
  const geoJsonClickHandlersRef = useRef<Map<string, (event: maplibregl.MapLayerMouseEvent) => void>>(new Map());
  const geoJsonEnterHandlersRef = useRef<Map<string, () => void>>(new Map());
  const geoJsonLeaveHandlersRef = useRef<Map<string, () => void>>(new Map());
  const geoJsonMoveHandlersRef = useRef<Map<string, (event: maplibregl.MapLayerMouseEvent) => void>>(new Map());

  function detachInteractions(map: maplibregl.Map) {
    if (!interactionLayerRef.current) {
      // still clean overlays even if primary is null
    } else {
      const activeLayer = interactionLayerRef.current;
      if (clickHandlerRef.current) {
        map.off("click", activeLayer, clickHandlerRef.current);
        clickHandlerRef.current = null;
      }
      if (enterHandlerRef.current) {
        map.off("mouseenter", activeLayer, enterHandlerRef.current);
        enterHandlerRef.current = null;
      }
      if (leaveHandlerRef.current) {
        map.off("mouseleave", activeLayer, leaveHandlerRef.current);
        leaveHandlerRef.current = null;
      }
      if (moveHandlerRef.current) {
        map.off("mousemove", activeLayer, moveHandlerRef.current);
        moveHandlerRef.current = null;
      }
      interactionLayerRef.current = null;
    }
    if (hoverPopupRef.current) {
      hoverPopupRef.current.remove();
      hoverPopupRef.current = null;
    }
    // Detach overlay interactions
    for (const olLayerId of overlayInteractionLayersRef.current) {
      const clickH = overlayClickHandlersRef.current.get(olLayerId);
      if (clickH) map.off("click", olLayerId, clickH);
      const enterH = overlayEnterHandlersRef.current.get(olLayerId);
      if (enterH) map.off("mouseenter", olLayerId, enterH);
      const leaveH = overlayLeaveHandlersRef.current.get(olLayerId);
      if (leaveH) map.off("mouseleave", olLayerId, leaveH);
      const moveH = overlayMoveHandlersRef.current.get(olLayerId);
      if (moveH) map.off("mousemove", olLayerId, moveH);
    }
    overlayInteractionLayersRef.current = [];
    overlayClickHandlersRef.current.clear();
    overlayEnterHandlersRef.current.clear();
    overlayLeaveHandlersRef.current.clear();
    overlayMoveHandlersRef.current.clear();
    // Detach GeoJSON layer interactions
    for (const gjLayerId of geoJsonInteractionLayersRef.current) {
      const clickH = geoJsonClickHandlersRef.current.get(gjLayerId);
      if (clickH) map.off("click", gjLayerId, clickH);
      const enterH = geoJsonEnterHandlersRef.current.get(gjLayerId);
      if (enterH) map.off("mouseenter", gjLayerId, enterH);
      const leaveH = geoJsonLeaveHandlersRef.current.get(gjLayerId);
      if (leaveH) map.off("mouseleave", gjLayerId, leaveH);
      const moveH = geoJsonMoveHandlersRef.current.get(gjLayerId);
      if (moveH) map.off("mousemove", gjLayerId, moveH);
    }
    geoJsonInteractionLayersRef.current = [];
    geoJsonClickHandlersRef.current.clear();
    geoJsonEnterHandlersRef.current.clear();
    geoJsonLeaveHandlersRef.current.clear();
    geoJsonMoveHandlersRef.current.clear();
  }

  const emptyStyle: maplibregl.StyleSpecification = {
    version: 8,
    name: "territorial-intelligence",
    sources: {},
    layers: [
      {
        id: "background",
        type: "background",
        paint: { "background-color": "#f6f4ee" },
      },
    ],
  };

  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: emptyStyle,
      center,
      zoom,
      attributionControl: false,
      maxZoom: 18,
      minZoom: 0,
    });

    map.addControl(
      new maplibregl.NavigationControl({
        showCompass: true,
        showZoom: true,
      }),
      "top-right",
    );
    if (typeof maplibregl.FullscreenControl === "function") {
      map.addControl(new maplibregl.FullscreenControl(), "top-right");
    }
    if (typeof maplibregl.GeolocateControl === "function") {
      map.addControl(
        new maplibregl.GeolocateControl({
          positionOptions: { enableHighAccuracy: true },
          trackUserLocation: false,
          showUserLocation: true,
        }),
        "top-right",
      );
    }
    if (typeof maplibregl.ScaleControl === "function") {
      map.addControl(
        new maplibregl.ScaleControl({
          maxWidth: 120,
          unit: "metric",
        }),
        "bottom-left",
      );
    }
    if (typeof maplibregl.AttributionControl === "function") {
      map.addControl(
        new maplibregl.AttributionControl({
          compact: true,
        }),
        "bottom-right",
      );
    }
    map.on("zoomend", () => {
      onZoomChange?.(Math.round(map.getZoom()));
    });
    const errorHandler = (event: maplibregl.ErrorEvent) => {
      const reason = event.error instanceof Error ? event.error.message : "falha ao carregar mapa vetorial";
      const normalizedReason = reason.toLowerCase();
      if (normalizedReason.includes("abort") || normalizedReason.includes("aborted")) {
        return;
      }
      onError?.(reason);
    };
    map.on("error", errorHandler);

    mapRef.current = map;

    return () => {
      detachInteractions(map);
      map.off("error", errorHandler);
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const updateLayers = () => {
      const currentZoom = Math.round(map.getZoom());
      const resolved = layers ? resolveLayerForZoom(layers, currentZoom, defaultLayerId) : undefined;
      const layerId = resolved?.id ?? defaultLayerId ?? "territory_municipality";
      const layerKind = resolved?.layer_kind ?? "polygon";
      const effectiveVizMode = layerKind === "point" && vizMode === "choropleth" ? "points" : vizMode;
      setCurrentLayerId(layerId);

      const tileUrl = buildTileUrl(tileBaseUrl, layerId);
      const basemapTileUrl = resolveBasemapTileUrl(basemapMode, basemapTileUrls);
      const basemapAttribution = resolveBasemapAttribution(basemapMode);
      const polygonFillOpacity = resolvePolygonFillOpacity(basemapMode);
      const boundaryPaint = resolveBoundaryPaint(basemapMode);

      detachInteractions(map);

      for (const lid of ["selection-highlight", "fill-layer", "line-layer", "points-layer", "heatmap-layer", "label-layer"]) {
        if (map.getLayer(lid)) map.removeLayer(lid);
      }
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
      if (map.getLayer(BASEMAP_LAYER_ID)) map.removeLayer(BASEMAP_LAYER_ID);
      if (map.getSource(BASEMAP_SOURCE_ID)) map.removeSource(BASEMAP_SOURCE_ID);

      // Cleanup previous overlay layers and sources
      const allMapLayers = map.getStyle()?.layers ?? [];
      for (const lyr of allMapLayers) {
        if (lyr.id.startsWith("overlay-layer-") || lyr.id.startsWith("overlay-border-") || lyr.id.startsWith("geojson-")) {
          map.removeLayer(lyr.id);
        }
      }
      const allSources = Object.keys(map.getStyle()?.sources ?? {});
      for (const srcId of allSources) {
        if (srcId.startsWith("overlay-source-") || srcId.startsWith("geojson-source-")) {
          map.removeSource(srcId);
        }
      }

      try {
        if (basemapTileUrl) {
          map.addSource(BASEMAP_SOURCE_ID, {
            type: "raster",
            tiles: [basemapTileUrl],
            tileSize: 256,
            maxzoom: 20,
            attribution: basemapAttribution,
          });
          map.addLayer({
            id: BASEMAP_LAYER_ID,
            type: "raster",
            source: BASEMAP_SOURCE_ID,
            paint: {
              "raster-opacity": 1,
            },
          });
        }

        map.addSource(SOURCE_ID, {
          type: "vector",
          tiles: [tileUrl],
          maxzoom: 18,
        });

        if (layerKind === "line") {
          map.addLayer({
            id: "line-layer",
            type: "line",
            source: SOURCE_ID,
            "source-layer": layerId,
            paint: {
              "line-color": buildFillColor(colorStops),
              "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],
                10,
                0.8,
                13,
                1.4,
                16,
                2.2,
              ] as maplibregl.ExpressionSpecification,
              "line-opacity": 0.9,
            },
          });
        } else if (boundaryOnly) {
          // Boundary-only mode: subtle contour line, no fill
          map.addLayer({
            id: "line-layer",
            type: "line",
            source: SOURCE_ID,
            "source-layer": layerId,
            paint: {
              "line-color": "rgba(15, 23, 42, 0.45)",
              "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],
                8, 0.6,
                12, 1.2,
                16, 1.8,
              ] as maplibregl.ExpressionSpecification,
              "line-opacity": 0.7,
            },
          });
        } else if (effectiveVizMode === "choropleth" || effectiveVizMode === undefined) {
          map.addLayer({
            id: "fill-layer",
            type: "fill",
            source: SOURCE_ID,
            "source-layer": layerId,
            paint: {
              "fill-color": buildFillColor(colorStops),
              "fill-opacity": polygonFillOpacity,
            },
          });
          map.addLayer({
            id: "line-layer",
            type: "line",
            source: SOURCE_ID,
            "source-layer": layerId,
            paint: {
              "line-color": boundaryPaint.color,
              "line-width": boundaryPaint.width,
            },
          });
        } else if (effectiveVizMode === "points") {
          map.addLayer({
            id: "points-layer",
            type: "circle",
            source: SOURCE_ID,
            "source-layer": layerId,
            filter: buildHasValueFilter(),
            paint: {
              "circle-radius": ["interpolate", ["linear"], buildNumericValueExpression(), 0, 3, 50, 8, 100, 16] as maplibregl.ExpressionSpecification,
              "circle-color": buildFillColor(colorStops),
              "circle-opacity": 0.8,
              "circle-stroke-width": 1,
              "circle-stroke-color": "#fff",
            },
          });
        } else if (effectiveVizMode === "heatmap") {
          map.addLayer({
            id: "heatmap-layer",
            type: "heatmap",
            source: SOURCE_ID,
            "source-layer": layerId,
            filter: buildHasValueFilter(),
            paint: {
              "heatmap-weight": ["interpolate", ["linear"], buildNumericValueExpression(), 0, 0, 100, 1] as maplibregl.ExpressionSpecification,
              "heatmap-intensity": 1,
              "heatmap-radius": 30,
              "heatmap-opacity": 0.7,
              "heatmap-color": [
                "interpolate",
                ["linear"],
                ["heatmap-density"],
                0,
                "rgba(33,102,172,0)",
                0.2,
                "rgb(103,169,207)",
                0.4,
                "rgb(209,229,240)",
                0.6,
                "rgb(253,219,199)",
                0.8,
                "rgb(239,138,98)",
                1,
                "rgb(178,24,43)",
              ] as maplibregl.ExpressionSpecification,
            },
          });
        } else {
          const gapExpression: maplibregl.ExpressionSpecification = [
            "interpolate",
            ["linear"],
            buildNumericValueExpression(),
            0,
            "#0f766e",
            40,
            "#f59e0b",
            80,
            "#b91c1c",
          ] as maplibregl.ExpressionSpecification;
          const criticalExpression: maplibregl.ExpressionSpecification = [
            "case",
            ["!", buildHasValueFilter()],
            "rgba(0,0,0,0.10)",
            [">=", buildNumericValueExpression(), 80],
            "#b91c1c",
            "rgba(15, 23, 42, 0.08)",
          ] as maplibregl.ExpressionSpecification;
          map.addLayer({
            id: "fill-layer",
            type: "fill",
            source: SOURCE_ID,
            "source-layer": layerId,
            paint: {
              "fill-color": effectiveVizMode === "gap" ? gapExpression : criticalExpression,
              "fill-opacity": polygonFillOpacity,
            },
          });
          map.addLayer({
            id: "line-layer",
            type: "line",
            source: SOURCE_ID,
            "source-layer": layerId,
            paint: {
              "line-color": boundaryPaint.color,
              "line-width": boundaryPaint.width,
            },
          });
        }
        if (showContextLabels) {
          const labelMinZoom = layerKind === "line" ? 12 : layerKind === "point" ? 11 : 9;
          const labelLayout: Record<string, unknown> = {
            "text-field": buildLabelFieldExpression(),
            "text-size": [
              "interpolate",
              ["linear"],
              ["zoom"],
              labelMinZoom,
              10,
              14,
              12,
              17,
              13,
            ],
            "text-font": ["Open Sans Semibold", "Arial Unicode MS Regular"],
            "text-max-width": 10,
            "text-allow-overlap": false,
            "text-padding": 2,
          };
          if (layerKind === "line") {
            labelLayout["symbol-placement"] = "line";
            labelLayout["symbol-spacing"] = 320;
          }
          map.addLayer({
            id: "label-layer",
            type: "symbol",
            source: SOURCE_ID,
            "source-layer": layerId,
            filter: buildHasLabelFilter(),
            minzoom: labelMinZoom,
            layout: labelLayout as maplibregl.SymbolLayerSpecification["layout"],
            paint: {
              "text-color": "#1f2937",
              "text-halo-color": "rgba(255,255,255,0.92)",
              "text-halo-width": 1.1,
            },
          });
        }
      } catch (error) {
        const reason = error instanceof Error ? error.message : "falha ao montar camadas vetoriais";
        onError?.(reason);
        return;
      }

      const interactionLayer =
        layerKind === "line" ? "line-layer" : effectiveVizMode === "points" ? "points-layer" : "fill-layer";
      if (map.getLayer(interactionLayer)) {
        const clickHandler = (event: maplibregl.MapLayerMouseEvent) => {
          const feature = event.features?.[0];
          if (!feature || !feature.properties) return;
          const properties = feature.properties as Record<string, unknown>;
          const rawValue = properties.val ?? properties.value;
          const numericValue =
            typeof rawValue === "number"
              ? rawValue
              : typeof rawValue === "string" && rawValue.trim() !== ""
                ? Number(rawValue)
                : undefined;
          const tidSource =
            properties.tid ??
            properties.territory_id ??
            properties.id ??
            properties.feature_id ??
            "";
          const tnameSource =
            properties.tname ??
            properties.territory_name ??
            properties.name ??
            properties.label ??
            "";
          const labelSource = properties.label ?? properties.name ?? properties.territory_name ?? null;
          const categorySource =
            properties.category ??
            properties.road_class ??
            properties.poi_category ??
            properties.class ??
            null;
          onFeatureClick?.({
            tid: String(tidSource ?? ""),
            tname: String(tnameSource ?? ""),
            val: typeof numericValue === "number" && Number.isFinite(numericValue) ? numericValue : undefined,
            label: labelSource == null ? undefined : String(labelSource),
            category: categorySource == null ? undefined : String(categorySource),
            lon: Number.isFinite(event.lngLat.lng) ? event.lngLat.lng : undefined,
            lat: Number.isFinite(event.lngLat.lat) ? event.lngLat.lat : undefined,
            layerKind: layerKind,
            rawProperties: properties,
          });
        };
        const enterHandler = () => {
          map.getCanvas().style.cursor = "pointer";
        };
        const moveHandler = (event: maplibregl.MapLayerMouseEvent) => {
          const feature = event.features?.[0];
          if (!feature?.properties) {
            if (hoverPopupRef.current) {
              hoverPopupRef.current.remove();
              hoverPopupRef.current = null;
            }
            return;
          }
          const properties = feature.properties as Record<string, unknown>;
          const rawValue = properties.val ?? properties.value;
          const nameToken = String(
            properties.tname ?? properties.territory_name ?? properties.name ?? properties.label ?? "n/d",
          );
          const valueToken = rawValue == null || rawValue === "" ? "n/d" : String(rawValue);
          const trendToken = tooltipContext?.trend ?? String(properties.trend ?? "n/d");
          const sourceToken = tooltipContext?.source ?? String(properties.source ?? "n/d");
          const updatedToken = tooltipContext?.updatedAt ?? String(properties.updated_at ?? "n/d");
          const indicatorToken = tooltipContext?.indicatorName ?? String(properties.metric ?? "indicador");

          const content = [
            `<strong>${nameToken}</strong>`,
            `${indicatorToken}: ${valueToken}`,
            `Tendencia: ${trendToken}`,
            `Fonte: ${sourceToken}`,
            `Atualizacao: ${updatedToken}`,
          ].join("<br/>");

          if (!hoverPopupRef.current) {
            hoverPopupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 12 });
          }

          hoverPopupRef.current.setLngLat(event.lngLat).setHTML(content).addTo(map);
        };
        const leaveHandler = () => {
          map.getCanvas().style.cursor = "";
          if (hoverPopupRef.current) {
            hoverPopupRef.current.remove();
            hoverPopupRef.current = null;
          }
        };

        map.on("click", interactionLayer, clickHandler);
        map.on("mouseenter", interactionLayer, enterHandler);
        map.on("mousemove", interactionLayer, moveHandler);
        map.on("mouseleave", interactionLayer, leaveHandler);

        interactionLayerRef.current = interactionLayer;
        clickHandlerRef.current = clickHandler;
        enterHandlerRef.current = enterHandler;
        moveHandlerRef.current = moveHandler;
        leaveHandlerRef.current = leaveHandler;
      }

      // --- Overlay layers ---
      const enabledOverlays = (overlays ?? []).filter((ol) => ol.enabled);
      for (const overlay of enabledOverlays) {
        const olSourceId = `overlay-source-${overlay.id}`;
        const olLayerId = `overlay-layer-${overlay.id}`;
        const olTileUrl = buildTileUrl(tileBaseUrl, overlay.tileLayerId);

        try {
          map.addSource(olSourceId, {
            type: "vector",
            tiles: [olTileUrl],
            maxzoom: 18,
          });

          if (overlay.vizType === "circle") {
            const paintOpts: Record<string, unknown> = {
              "circle-radius": [
                "interpolate",
                ["linear"],
                ["zoom"],
                10, 3,
                14, 6,
                18, 10,
              ],
              "circle-color": overlay.color,
              "circle-opacity": overlay.opacity ?? 0.8,
              "circle-stroke-width": 1.2,
              "circle-stroke-color": "#fff",
            };
            const layerDef: Record<string, unknown> = {
              id: olLayerId,
              type: "circle",
              source: olSourceId,
              "source-layer": overlay.tileLayerId,
              paint: paintOpts,
            };
            if (overlay.filter) {
              layerDef.filter = overlay.filter;
            }
            if (overlay.minZoom != null) {
              layerDef.minzoom = overlay.minZoom;
            }
            map.addLayer(layerDef as maplibregl.LayerSpecification);
          } else if (overlay.vizType === "fill") {
            const paintOpts: Record<string, unknown> = {
              "fill-color": overlay.color,
              "fill-opacity": overlay.opacity ?? 0.25,
            };
            const layerDef: Record<string, unknown> = {
              id: olLayerId,
              type: "fill",
              source: olSourceId,
              "source-layer": overlay.tileLayerId,
              paint: paintOpts,
            };
            if (overlay.filter) {
              layerDef.filter = overlay.filter;
            }
            if (overlay.minZoom != null) {
              layerDef.minzoom = overlay.minZoom;
            }
            map.addLayer(layerDef as maplibregl.LayerSpecification);
            // Also add border for fill overlays
            const olBorderId = `overlay-border-${overlay.id}`;
            map.addLayer({
              id: olBorderId,
              type: "line",
              source: olSourceId,
              "source-layer": overlay.tileLayerId,
              paint: {
                "line-color": overlay.color,
                "line-width": 1.5,
                "line-opacity": 0.6,
              },
              ...(overlay.filter ? { filter: overlay.filter } : {}),
              ...(overlay.minZoom != null ? { minzoom: overlay.minZoom } : {}),
            } as maplibregl.LayerSpecification);
          } else if (overlay.vizType === "heatmap") {
            const layerDef: Record<string, unknown> = {
              id: olLayerId,
              type: "heatmap",
              source: olSourceId,
              "source-layer": overlay.tileLayerId,
              paint: {
                "heatmap-weight": 1,
                "heatmap-intensity": 1,
                "heatmap-radius": 25,
                "heatmap-opacity": overlay.opacity ?? 0.6,
                "heatmap-color": [
                  "interpolate",
                  ["linear"],
                  ["heatmap-density"],
                  0, "rgba(33,102,172,0)",
                  0.2, "rgb(103,169,207)",
                  0.4, "rgb(209,229,240)",
                  0.6, "rgb(253,219,199)",
                  0.8, "rgb(239,138,98)",
                  1, "rgb(178,24,43)",
                ],
              },
            };
            if (overlay.filter) {
              layerDef.filter = overlay.filter;
            }
            if (overlay.minZoom != null) {
              layerDef.minzoom = overlay.minZoom;
            }
            map.addLayer(layerDef as maplibregl.LayerSpecification);
          }

          // Overlay interactions (for circle and fill types - heatmap has no feature interaction)
          if (overlay.vizType !== "heatmap" && map.getLayer(olLayerId)) {
            const olClickHandler = (event: maplibregl.MapLayerMouseEvent) => {
              const feature = event.features?.[0];
              if (!feature?.properties) return;
              const props = feature.properties as Record<string, unknown>;
              const tidSource = props.tid ?? props.territory_id ?? props.id ?? props.poi_id ?? "";
              const tnameSource = props.tname ?? props.territory_name ?? props.name ?? props.label ?? "";
              const rawVal = props.val ?? props.value;
              const numVal = typeof rawVal === "number" ? rawVal : typeof rawVal === "string" && rawVal.trim() !== "" ? Number(rawVal) : undefined;
              onFeatureClick?.({
                tid: String(tidSource ?? ""),
                tname: String(tnameSource ?? ""),
                val: typeof numVal === "number" && Number.isFinite(numVal) ? numVal : undefined,
                label: props.label == null ? undefined : String(props.label),
                category: props.category == null ? undefined : String(props.category),
                lon: Number.isFinite(event.lngLat.lng) ? event.lngLat.lng : undefined,
                lat: Number.isFinite(event.lngLat.lat) ? event.lngLat.lat : undefined,
                layerKind: overlay.vizType === "circle" ? "point" : "polygon",
                rawProperties: props,
                overlayId: overlay.id,
              });
            };
            const olEnterHandler = () => { map.getCanvas().style.cursor = "pointer"; };
            const olLeaveHandler = () => {
              map.getCanvas().style.cursor = "";
              if (hoverPopupRef.current) { hoverPopupRef.current.remove(); hoverPopupRef.current = null; }
            };
            const olMoveHandler = (event: maplibregl.MapLayerMouseEvent) => {
              const feature = event.features?.[0];
              if (!feature?.properties) {
                if (hoverPopupRef.current) { hoverPopupRef.current.remove(); hoverPopupRef.current = null; }
                return;
              }
              const props = feature.properties as Record<string, unknown>;
              const nameToken = String(props.tname ?? props.name ?? props.label ?? "n/d");
              const catToken = props.category ? String(props.category) : null;
              const subcatToken = props.subcategory ? String(props.subcategory) : null;
              const lines = [`<strong>${nameToken}</strong>`, `Camada: ${overlay.label}`];
              if (catToken) lines.push(`Categoria: ${catToken}`);
              if (subcatToken) lines.push(`Subcategoria: ${subcatToken}`);
              const content = lines.join("<br/>");
              if (!hoverPopupRef.current) {
                hoverPopupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 12 });
              }
              hoverPopupRef.current.setLngLat(event.lngLat).setHTML(content).addTo(map);
            };
            map.on("click", olLayerId, olClickHandler);
            map.on("mouseenter", olLayerId, olEnterHandler);
            map.on("mousemove", olLayerId, olMoveHandler);
            map.on("mouseleave", olLayerId, olLeaveHandler);
            overlayInteractionLayersRef.current.push(olLayerId);
            overlayClickHandlersRef.current.set(olLayerId, olClickHandler);
            overlayEnterHandlersRef.current.set(olLayerId, olEnterHandler);
            overlayLeaveHandlersRef.current.set(olLayerId, olLeaveHandler);
            overlayMoveHandlersRef.current.set(olLayerId, olMoveHandler);
          }
        } catch (overlayError) {
          const reason = overlayError instanceof Error ? overlayError.message : `falha ao montar overlay ${overlay.id}`;
          onError?.(reason);
        }
      }

      // --- GeoJSON cluster layers ---
      const enabledGeoJsonLayers = (geoJsonLayers ?? []).filter((gl) => gl.enabled !== false);
      for (const gjLayer of enabledGeoJsonLayers) {
        const gjSourceId = `geojson-source-${gjLayer.id}`;
        const gjClusterCircleId = `geojson-clusters-${gjLayer.id}`;
        const gjClusterLabelId = `geojson-cluster-label-${gjLayer.id}`;
        const gjUnclusteredId = `geojson-unclustered-${gjLayer.id}`;

        try {
          const sourceConfig: Record<string, unknown> = {
            type: "geojson",
            data: gjLayer.data,
            cluster: true,
            clusterMaxZoom: gjLayer.clusterMaxZoom ?? 14,
            clusterRadius: gjLayer.clusterRadius ?? 50,
          };
          if (gjLayer.clusterProperties) {
            sourceConfig.clusterProperties = gjLayer.clusterProperties;
          }
          map.addSource(gjSourceId, sourceConfig as maplibregl.SourceSpecification);

          // Cluster circles
          map.addLayer({
            id: gjClusterCircleId,
            type: "circle",
            source: gjSourceId,
            filter: ["has", "point_count"],
            paint: {
              "circle-color": gjLayer.color,
              "circle-radius": [
                "step",
                ["get", "point_count"],
                16, 5, 20, 10, 26, 30, 34, 60, 42,
              ] as maplibregl.ExpressionSpecification,
              "circle-opacity": 0.7,
              "circle-stroke-width": 2,
              "circle-stroke-color": "#fff",
            },
            ...(gjLayer.minZoom != null ? { minzoom: gjLayer.minZoom } : {}),
          } as maplibregl.LayerSpecification);

          // Cluster label
          const clusterLabel = gjLayer.clusterLabelExpression ?? [
            "to-string", ["get", "point_count"],
          ] as maplibregl.ExpressionSpecification;
          map.addLayer({
            id: gjClusterLabelId,
            type: "symbol",
            source: gjSourceId,
            filter: ["has", "point_count"],
            layout: {
              "text-field": clusterLabel,
              "text-size": 11,
              "text-allow-overlap": true,
              "text-font": ["Open Sans Semibold", "Arial Unicode MS Regular"],
            },
            paint: {
              "text-color": "#fff",
            },
            ...(gjLayer.minZoom != null ? { minzoom: gjLayer.minZoom } : {}),
          } as maplibregl.LayerSpecification);

          // Unclustered proportional points
          const defaultRadius = ["max", 4, ["min", 18, ["*", 0.35, ["sqrt", ["coalesce", ["get", "voters"], 1]]]]] as maplibregl.ExpressionSpecification;
          map.addLayer({
            id: gjUnclusteredId,
            type: "circle",
            source: gjSourceId,
            filter: ["!", ["has", "point_count"]],
            paint: {
              "circle-radius": gjLayer.radiusExpression ?? defaultRadius,
              "circle-color": gjLayer.color,
              "circle-opacity": gjLayer.opacity ?? 0.65,
              "circle-stroke-width": gjLayer.strokeWidth ?? 1.5,
              "circle-stroke-color": gjLayer.strokeColor ?? "#fff",
            },
            ...(gjLayer.minZoom != null ? { minzoom: gjLayer.minZoom } : {}),
          } as maplibregl.LayerSpecification);

          // GeoJSON layer interactions
          const gjClickHandler = (event: maplibregl.MapLayerMouseEvent) => {
            const feature = event.features?.[0];
            if (!feature?.properties) return;
            const props = feature.properties as Record<string, unknown>;
            const tidSource = props.tid ?? props.territory_id ?? props.id ?? "";
            const tnameSource = props.tname ?? props.territory_name ?? props.name ?? "";
            const rawVal = props.voters ?? props.val ?? props.value;
            const numVal = typeof rawVal === "number" ? rawVal : typeof rawVal === "string" && rawVal.trim() !== "" ? Number(rawVal) : undefined;
            onFeatureClick?.({
              tid: String(tidSource ?? ""),
              tname: String(tnameSource ?? ""),
              val: typeof numVal === "number" && Number.isFinite(numVal) ? numVal : undefined,
              label: props.label == null ? undefined : String(props.label ?? tnameSource),
              category: props.category == null ? undefined : String(props.category),
              lon: Number.isFinite(event.lngLat.lng) ? event.lngLat.lng : undefined,
              lat: Number.isFinite(event.lngLat.lat) ? event.lngLat.lat : undefined,
              layerKind: "point",
              rawProperties: props,
              overlayId: gjLayer.id,
            });
          };
          const gjEnterHandler = () => { map.getCanvas().style.cursor = "pointer"; };
          const gjLeaveHandler = () => {
            map.getCanvas().style.cursor = "";
            if (hoverPopupRef.current) { hoverPopupRef.current.remove(); hoverPopupRef.current = null; }
          };
          const gjMoveHandler = (event: maplibregl.MapLayerMouseEvent) => {
            const feature = event.features?.[0];
            if (!feature?.properties) {
              if (hoverPopupRef.current) { hoverPopupRef.current.remove(); hoverPopupRef.current = null; }
              return;
            }
            const props = feature.properties as Record<string, unknown>;
            const content = gjLayer.tooltipFn
              ? gjLayer.tooltipFn(props)
              : `<strong>${String(props.tname ?? props.name ?? "n/d")}</strong>`;
            if (!hoverPopupRef.current) {
              hoverPopupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 12 });
            }
            hoverPopupRef.current.setLngLat(event.lngLat).setHTML(content).addTo(map);
          };
          // Interactions on unclustered points
          map.on("click", gjUnclusteredId, gjClickHandler);
          map.on("mouseenter", gjUnclusteredId, gjEnterHandler);
          map.on("mousemove", gjUnclusteredId, gjMoveHandler);
          map.on("mouseleave", gjUnclusteredId, gjLeaveHandler);
          geoJsonInteractionLayersRef.current.push(gjUnclusteredId);
          geoJsonClickHandlersRef.current.set(gjUnclusteredId, gjClickHandler);
          geoJsonEnterHandlersRef.current.set(gjUnclusteredId, gjEnterHandler);
          geoJsonLeaveHandlersRef.current.set(gjUnclusteredId, gjLeaveHandler);
          geoJsonMoveHandlersRef.current.set(gjUnclusteredId, gjMoveHandler);

          // Cluster click — pointer and optional tooltip
          const gjClusterEnter = () => { map.getCanvas().style.cursor = "pointer"; };
          const gjClusterLeave = () => {
            map.getCanvas().style.cursor = "";
            if (hoverPopupRef.current) { hoverPopupRef.current.remove(); hoverPopupRef.current = null; }
          };
          const gjClusterMove = (event: maplibregl.MapLayerMouseEvent) => {
            const feature = event.features?.[0];
            if (!feature?.properties) return;
            const props = feature.properties as Record<string, unknown>;
            const content = gjLayer.clusterTooltipFn
              ? gjLayer.clusterTooltipFn(props)
              : `<strong>${String(props.point_count ?? "?")} pontos agrupados</strong>`;
            if (!hoverPopupRef.current) {
              hoverPopupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 12 });
            }
            hoverPopupRef.current.setLngLat(event.lngLat).setHTML(content).addTo(map);
          };
          const gjClusterClick = (event: maplibregl.MapLayerMouseEvent) => {
            const feature = event.features?.[0];
            if (!feature) return;
            const clusterId = feature.properties?.cluster_id;
            if (clusterId == null) return;
            const src = map.getSource(gjSourceId);
            if (src && "getClusterExpansionZoom" in src) {
              (src as maplibregl.GeoJSONSource).getClusterExpansionZoom(clusterId as number).then((expZoom) => {
                const geo = feature.geometry;
                if (geo.type === "Point") {
                  safeEaseTo(map, {
                    center: geo.coordinates as [number, number],
                    zoom: Math.min(expZoom, 18),
                    duration: 400,
                    essential: true,
                  });
                }
              });
            }
          };
          map.on("click", gjClusterCircleId, gjClusterClick);
          map.on("mouseenter", gjClusterCircleId, gjClusterEnter);
          map.on("mousemove", gjClusterCircleId, gjClusterMove);
          map.on("mouseleave", gjClusterCircleId, gjClusterLeave);
          geoJsonInteractionLayersRef.current.push(gjClusterCircleId);
          geoJsonClickHandlersRef.current.set(gjClusterCircleId, gjClusterClick);
          geoJsonEnterHandlersRef.current.set(gjClusterCircleId, gjClusterEnter);
          geoJsonLeaveHandlersRef.current.set(gjClusterCircleId, gjClusterLeave);
          geoJsonMoveHandlersRef.current.set(gjClusterCircleId, gjClusterMove);
        } catch (gjError) {
          const reason = gjError instanceof Error ? gjError.message : `falha ao montar GeoJSON layer ${gjLayer.id}`;
          onError?.(reason);
        }
      }
    };

    if (!map.isStyleLoaded()) {
      map.once("styledata", updateLayers);
      return;
    }

    updateLayers();
  }, [
    tileBaseUrl,
    layers,
    defaultLayerId,
    vizMode,
    colorStops,
    onFeatureClick,
    onError,
    basemapMode,
    basemapTileUrls,
    showContextLabels,
    tooltipContext,
    overlays,
    geoJsonLayers,
    boundaryOnly,
  ]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !layers) return;

    const handleZoom = () => {
      const z = Math.round(map.getZoom());
      const resolved = resolveLayerForZoom(layers, z, defaultLayerId);
      if (resolved && resolved.id !== currentLayerId) {
        setCurrentLayerId(resolved.id);
      }
    };

    map.on("zoomend", handleZoom);
    return () => {
      map.off("zoomend", handleZoom);
    };
  }, [layers, defaultLayerId, currentLayerId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const clampedZoom = Math.max(0, Math.min(18, zoom));
    if (Math.abs(map.getZoom() - clampedZoom) < 0.01) {
      return;
    }
    safeEaseTo(map, { zoom: clampedZoom, duration: 250, essential: true });
  }, [zoom]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    safeEaseTo(map, { center, duration: 500, essential: true });
  }, [center, resetViewSignal]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (map.getLayer("selection-highlight")) {
      map.removeLayer("selection-highlight");
    }

    if (!selectedTerritoryId || !currentLayerId || !map.getSource(SOURCE_ID)) {
      return;
    }

    map.addLayer({
      id: "selection-highlight",
      type: "line",
      source: SOURCE_ID,
      "source-layer": currentLayerId,
      filter: ["==", ["get", "tid"], selectedTerritoryId],
      paint: {
        "line-color": "#1e3a5f",
        "line-width": 3,
      },
    });
  }, [selectedTerritoryId, currentLayerId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedTerritoryId || !currentLayerId) {
      return;
    }

    const focusTerritory = () => {
      if (!map.getSource(SOURCE_ID)) {
        return;
      }
      const features = map.querySourceFeatures(SOURCE_ID, { sourceLayer: currentLayerId });
      const feature = features.find((item) => String(item.properties?.tid ?? "") === selectedTerritoryId);
      if (!feature?.geometry) {
        return;
      }

      const bounds = buildBoundsFromGeometry(feature.geometry);
      if (!bounds) {
        return;
      }

      const [sw, ne] = bounds as [[number, number], [number, number]];
      const isPointLike = Math.abs(sw[0] - ne[0]) < 1e-9 && Math.abs(sw[1] - ne[1]) < 1e-9;
      if (isPointLike) {
        safeEaseTo(map, {
          center: [sw[0], sw[1]],
          zoom: Math.max(map.getZoom(), 14),
          duration: 550,
          essential: true,
        });
        return;
      }
      safeFitBounds(map, bounds as [[number, number], [number, number]]);
    };

    const tilesReady = typeof map.areTilesLoaded === "function" ? map.areTilesLoaded() : true;
    if (map.isStyleLoaded() && tilesReady) {
      focusTerritory();
      return;
    }
    map.once("idle", focusTerritory);
  }, [selectedTerritoryId, currentLayerId, focusTerritorySignal]);

  return (
    <div
      ref={containerRef}
      className="vector-map-container"
      style={{ width: "100%", height: "100%", minHeight: 400 }}
      role="application"
      aria-label="Mapa vetorial territorial"
    />
  );
}

