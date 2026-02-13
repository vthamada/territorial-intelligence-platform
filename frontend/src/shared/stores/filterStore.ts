import { create } from "zustand";

type FilterState = {
  period: string;
  level: string;
  metric: string;
  zoom: number;
  setPeriod: (period: string) => void;
  setLevel: (level: string) => void;
  setMetric: (metric: string) => void;
  setZoom: (zoom: number) => void;
  applyDefaults: () => void;
};

const DEFAULTS = {
  period: "2025",
  level: "municipality",
  metric: "MTE_NOVO_CAGED_SALDO_TOTAL",
  zoom: 4,
};

export const useFilterStore = create<FilterState>((set) => ({
  period: DEFAULTS.period,
  level: DEFAULTS.level,
  metric: DEFAULTS.metric,
  zoom: DEFAULTS.zoom,
  setPeriod: (period) => set({ period }),
  setLevel: (level) => set({ level }),
  setMetric: (metric) => set({ metric }),
  setZoom: (zoom) => set({ zoom }),
  applyDefaults: () => set(DEFAULTS),
}));
