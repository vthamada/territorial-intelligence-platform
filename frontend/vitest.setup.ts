import "@testing-library/jest-dom";
import { vi } from "vitest";

// Polyfill URL.createObjectURL / revokeObjectURL for jsdom (required by maplibre-gl worker blobs)
if (typeof URL.createObjectURL !== "function") {
  URL.createObjectURL = () => "blob:mock";
}
if (typeof URL.revokeObjectURL !== "function") {
  URL.revokeObjectURL = () => {};
}

// Mock maplibre-gl — WebGL is unavailable in jsdom
vi.mock("maplibre-gl", () => {
  const MapMock: any = vi.fn().mockImplementation(() => ({
    on: vi.fn(),
    off: vi.fn(),
    remove: vi.fn(),
    addControl: vi.fn(),
    addSource: vi.fn(),
    addLayer: vi.fn(),
    removeLayer: vi.fn(),
    removeSource: vi.fn(),
    getSource: vi.fn().mockReturnValue(undefined),
    getLayer: vi.fn().mockReturnValue(undefined),
    getStyle: vi.fn().mockReturnValue({ layers: [] }),
    getZoom: vi.fn().mockReturnValue(4),
    setFilter: vi.fn(),
    setPaintProperty: vi.fn(),
    getCanvas: vi.fn().mockReturnValue({ style: {} }),
    resize: vi.fn(),
    flyTo: vi.fn(),
    setCenter: vi.fn(),
    setZoom: vi.fn(),
    isStyleLoaded: vi.fn().mockReturnValue(true),
    loaded: vi.fn().mockReturnValue(true),
    triggerRepaint: vi.fn(),
    queryRenderedFeatures: vi.fn().mockReturnValue([]),
  }));
  return {
    default: {
      Map: MapMock,
      NavigationControl: vi.fn(),
    },
    Map: MapMock,
    NavigationControl: vi.fn(),
  };
});
