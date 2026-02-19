import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { MapLayerItem } from "../api/types";
import { resolveLayerForZoom } from "../hooks/useAutoLayerSwitch";

export type VizMode = "choropleth" | "points" | "heatmap" | "hotspots";
export type BasemapMode = "none" | "streets" | "light";

type BasemapTileUrls = {
  streets?: string;
  light?: string;
};

export type VectorMapProps = {
  tileBaseUrl: string;
  metric?: string;
  period?: string;
  domain?: string;
  layers?: MapLayerItem[];
  defaultLayerId?: string;
  vizMode?: VizMode;
  center?: [number, number];
  zoom?: number;
  onFeatureClick?: (feature: { tid: string; tname: string; val?: number }) => void;
  onZoomChange?: (zoom: number) => void;
  onError?: (message: string) => void;
  colorStops?: Array<{ value: number; color: string }>;
  selectedTerritoryId?: string;
  basemapMode?: BasemapMode;
  basemapTileUrls?: BasemapTileUrls;
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

function buildTileUrl(baseUrl: string, layerId: string, metric?: string, period?: string, domain?: string): string {
  const params = new URLSearchParams();
  if (metric) params.set("metric", metric);
  if (period) params.set("period", period);
  if (domain) params.set("domain", domain);
  const qs = params.toString();
  return `${baseUrl}/map/tiles/${layerId}/{z}/{x}/{y}.mvt${qs ? `?${qs}` : ""}`;
}

function buildFillColor(stops: Array<{ value: number; color: string }>): maplibregl.ExpressionSpecification {
  const expression: unknown[] = ["interpolate", ["linear"], ["coalesce", ["get", "val"], 0]];
  for (const stop of stops) {
    expression.push(stop.value);
    expression.push(stop.color);
  }
  return expression as maplibregl.ExpressionSpecification;
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

export function VectorMap({
  tileBaseUrl,
  metric,
  period,
  domain,
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
}: VectorMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [currentLayerId, setCurrentLayerId] = useState<string | undefined>(undefined);

  const interactionLayerRef = useRef<string | null>(null);
  const clickHandlerRef = useRef<((event: maplibregl.MapLayerMouseEvent) => void) | null>(null);
  const enterHandlerRef = useRef<(() => void) | null>(null);
  const leaveHandlerRef = useRef<(() => void) | null>(null);

  function detachInteractions(map: maplibregl.Map) {
    if (!interactionLayerRef.current) return;
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
    interactionLayerRef.current = null;
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

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.on("zoomend", () => {
      onZoomChange?.(Math.round(map.getZoom()));
    });
    const errorHandler = (event: maplibregl.ErrorEvent) => {
      const reason = event.error instanceof Error ? event.error.message : "falha ao carregar mapa vetorial";
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

      const tileUrl = buildTileUrl(tileBaseUrl, layerId, metric, period, domain);
      const basemapTileUrl = resolveBasemapTileUrl(basemapMode, basemapTileUrls);

      detachInteractions(map);

      for (const lid of ["selection-highlight", "fill-layer", "line-layer", "points-layer", "heatmap-layer"]) {
        if (map.getLayer(lid)) map.removeLayer(lid);
      }
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
      if (map.getLayer(BASEMAP_LAYER_ID)) map.removeLayer(BASEMAP_LAYER_ID);
      if (map.getSource(BASEMAP_SOURCE_ID)) map.removeSource(BASEMAP_SOURCE_ID);

      try {
        if (basemapTileUrl) {
          map.addSource(BASEMAP_SOURCE_ID, {
            type: "raster",
            tiles: [basemapTileUrl],
            tileSize: 256,
            maxzoom: 20,
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
        } else if (effectiveVizMode === "choropleth" || effectiveVizMode === undefined) {
          map.addLayer({
            id: "fill-layer",
            type: "fill",
            source: SOURCE_ID,
            "source-layer": layerId,
            paint: {
              "fill-color": buildFillColor(colorStops),
              "fill-opacity": 0.75,
            },
          });
          map.addLayer({
            id: "line-layer",
            type: "line",
            source: SOURCE_ID,
            "source-layer": layerId,
            paint: {
              "line-color": "#6b7280",
              "line-width": 0.5,
            },
          });
        } else if (effectiveVizMode === "points") {
          map.addLayer({
            id: "points-layer",
            type: "circle",
            source: SOURCE_ID,
            "source-layer": layerId,
            paint: {
              "circle-radius": ["interpolate", ["linear"], ["coalesce", ["get", "val"], 0], 0, 3, 50, 8, 100, 16] as maplibregl.ExpressionSpecification,
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
            paint: {
              "heatmap-weight": ["interpolate", ["linear"], ["coalesce", ["get", "val"], 0], 0, 0, 100, 1] as maplibregl.ExpressionSpecification,
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
          map.addLayer({
            id: "fill-layer",
            type: "fill",
            source: SOURCE_ID,
            "source-layer": layerId,
            paint: {
              "fill-color": [
                "case",
                [">=", ["coalesce", ["get", "val"], 0], 80],
                "#b91c1c",
                [">=", ["coalesce", ["get", "val"], 0], 50],
                "#d97706",
                "rgba(0,0,0,0.05)",
              ] as maplibregl.ExpressionSpecification,
              "fill-opacity": 0.7,
            },
          });
          map.addLayer({
            id: "line-layer",
            type: "line",
            source: SOURCE_ID,
            "source-layer": layerId,
            paint: {
              "line-color": "#6b7280",
              "line-width": 0.5,
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
          onFeatureClick?.({
            tid: String(feature.properties.tid ?? ""),
            tname: String(feature.properties.tname ?? ""),
            val: feature.properties.val != null ? Number(feature.properties.val) : undefined,
          });
        };
        const enterHandler = () => {
          map.getCanvas().style.cursor = "pointer";
        };
        const leaveHandler = () => {
          map.getCanvas().style.cursor = "";
        };

        map.on("click", interactionLayer, clickHandler);
        map.on("mouseenter", interactionLayer, enterHandler);
        map.on("mouseleave", interactionLayer, leaveHandler);

        interactionLayerRef.current = interactionLayer;
        clickHandlerRef.current = clickHandler;
        enterHandlerRef.current = enterHandler;
        leaveHandlerRef.current = leaveHandler;
      }
    };

    if (!map.isStyleLoaded()) {
      map.once("styledata", updateLayers);
      return;
    }

    updateLayers();
  }, [
    tileBaseUrl,
    metric,
    period,
    domain,
    layers,
    defaultLayerId,
    vizMode,
    colorStops,
    onFeatureClick,
    onError,
    basemapMode,
    basemapTileUrls,
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
