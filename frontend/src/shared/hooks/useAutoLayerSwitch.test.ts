import { describe, it, expect } from "vitest";
import { resolveLayerForZoom } from "./useAutoLayerSwitch";
import type { MapLayerItem } from "../api/types";

const LAYERS: MapLayerItem[] = [
  {
    id: "territory_municipality",
    label: "Municipios",
    territory_level: "municipality",
    is_official: true,
    source: "silver.dim_territory",
    default_visibility: true,
    zoom_min: 0,
    zoom_max: 8,
  },
  {
    id: "territory_district",
    label: "Distritos",
    territory_level: "district",
    is_official: true,
    source: "silver.dim_territory",
    default_visibility: true,
    zoom_min: 9,
    zoom_max: 11,
  },
  {
    id: "territory_census_sector",
    label: "Setores censitarios",
    territory_level: "census_sector",
    is_official: false,
    source: "silver.dim_territory",
    default_visibility: false,
    zoom_min: 12,
    zoom_max: null,
  },
];

describe("resolveLayerForZoom", () => {
  it("returns municipality layer for zoom 0-8", () => {
    for (const z of [0, 4, 8]) {
      const layer = resolveLayerForZoom(LAYERS, z);
      expect(layer?.id).toBe("territory_municipality");
    }
  });

  it("returns district layer for zoom 9-11", () => {
    for (const z of [9, 10, 11]) {
      const layer = resolveLayerForZoom(LAYERS, z);
      expect(layer?.id).toBe("territory_district");
    }
  });

  it("returns census_sector layer for zoom 12+", () => {
    for (const z of [12, 15, 18]) {
      const layer = resolveLayerForZoom(LAYERS, z);
      expect(layer?.id).toBe("territory_census_sector");
    }
  });

  it("falls back to default layer id when zoom is out of all ranges", () => {
    // If all layers had restrictive ranges, fallback should kick in
    const narrow: MapLayerItem[] = [
      { ...LAYERS[0], zoom_min: 5, zoom_max: 8 },
    ];
    const layer = resolveLayerForZoom(narrow, 0, "territory_municipality");
    expect(layer?.id).toBe("territory_municipality");
  });

  it("prefers default_visibility layer when multiple match", () => {
    const overlapping: MapLayerItem[] = [
      { ...LAYERS[0], default_visibility: false, zoom_min: 0, zoom_max: 10 },
      { ...LAYERS[1], default_visibility: true, zoom_min: 0, zoom_max: 10 },
    ];
    const layer = resolveLayerForZoom(overlapping, 5);
    expect(layer?.id).toBe("territory_district");
  });

  it("returns first layer when empty array gets fallback", () => {
    const layer = resolveLayerForZoom([], 5);
    expect(layer).toBeUndefined();
  });
});
