import { describe, expect, it } from "vitest";
import { useFilterStore } from "./filterStore";

describe("filterStore", () => {
  it("has default values", () => {
    const state = useFilterStore.getState();
    expect(state.period).toBe("2025");
    expect(state.level).toBe("municipality");
    expect(state.metric).toBe("MTE_NOVO_CAGED_SALDO_TOTAL");
    expect(state.zoom).toBe(4);
  });

  it("updates period", () => {
    useFilterStore.getState().setPeriod("2024");
    expect(useFilterStore.getState().period).toBe("2024");
  });

  it("updates level", () => {
    useFilterStore.getState().setLevel("district");
    expect(useFilterStore.getState().level).toBe("district");
  });

  it("updates metric", () => {
    useFilterStore.getState().setMetric("DATASUS_APS_COBERTURA");
    expect(useFilterStore.getState().metric).toBe("DATASUS_APS_COBERTURA");
  });

  it("updates zoom", () => {
    useFilterStore.getState().setZoom(12);
    expect(useFilterStore.getState().zoom).toBe(12);
  });

  it("resets to defaults", () => {
    useFilterStore.getState().setPeriod("2020");
    useFilterStore.getState().setLevel("census_sector");
    useFilterStore.getState().setMetric("CUSTOM");
    useFilterStore.getState().setZoom(15);
    useFilterStore.getState().applyDefaults();
    const state = useFilterStore.getState();
    expect(state.period).toBe("2025");
    expect(state.level).toBe("municipality");
    expect(state.metric).toBe("MTE_NOVO_CAGED_SALDO_TOTAL");
    expect(state.zoom).toBe(4);
  });
});
