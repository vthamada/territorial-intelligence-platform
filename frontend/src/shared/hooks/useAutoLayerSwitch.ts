import { useMemo } from "react";
import type { MapLayerItem } from "../api/types";

/**
 * Given a zoom level and the layer manifest from /v1/map/layers,
 * returns the layer whose zoom_min / zoom_max range contains the current zoom.
 *
 * Rules:
 *  - zoom_max === null  → no upper bound (matches any zoom >= zoom_min)
 *  - When multiple layers match, the one with default_visibility wins;
 *    if tied, the first match in manifest order is used.
 *  - If nothing matches the zoom level, the overall default layer is returned.
 */
export function resolveLayerForZoom(
  layers: MapLayerItem[],
  zoom: number,
  defaultLayerId?: string,
): MapLayerItem | undefined {
  const matches = layers.filter(
    (l) => zoom >= l.zoom_min && (l.zoom_max === null || zoom <= l.zoom_max),
  );

  if (matches.length === 0) {
    return layers.find((l) => l.id === defaultLayerId) ?? layers[0];
  }

  // prefer default_visibility layer among matches
  const visible = matches.find((l) => l.default_visibility);
  return visible ?? matches[0];
}

/**
 * React hook that returns the recommended layer for the current zoom level.
 *
 * @param layers   - layer manifest items (from /v1/map/layers)
 * @param zoom     - current map zoom level (integer or fractional)
 * @param defaultLayerId - fallback layer id when no range matches
 */
export function useAutoLayerSwitch(
  layers: MapLayerItem[] | undefined,
  zoom: number,
  defaultLayerId?: string,
): MapLayerItem | undefined {
  return useMemo(() => {
    if (!layers || layers.length === 0) return undefined;
    return resolveLayerForZoom(layers, zoom, defaultLayerId);
  }, [layers, zoom, defaultLayerId]);
}
