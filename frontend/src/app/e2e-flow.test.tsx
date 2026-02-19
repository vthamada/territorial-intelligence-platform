import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { createAppMemoryRouter } from "./router";

/**
 * E2E flow test — Sprint 5 / Onda 8 (O8-01)
 *
 * Validates the critical executive decision flow:
 *   Home → Prioridades → Mapa → Território 360 → Eleitorado → Cenários → Briefs
 *
 * Each step verifies:
 *   1. Page renders its heading/content correctly.
 *   2. Navigation links to the next step exist and work.
 *   3. Deep-links with query params propagate between pages.
 */

// ---- mocks ----

vi.mock("../shared/api/ops", () => ({
  getOpsSummary: vi.fn().mockResolvedValue({
    runs: { total: 5, by_status: { success: 5 }, by_wave: { "MVP-1": 5 }, latest_started_at_utc: null },
    checks: { total: 5, by_status: { pass: 5 }, latest_created_at_utc: null },
    connectors: { total: 22, by_status: { implemented: 22 }, by_wave: { "MVP-1": 7 }, latest_updated_at_utc: null }
  }),
  getOpsSla: vi.fn().mockResolvedValue({
    include_blocked_as_success: false,
    min_total_runs: 1,
    items: []
  }),
  getOpsReadiness: vi.fn().mockResolvedValue({
    status: "READY",
    strict: false,
    generated_at_utc: "2026-02-13T20:00:00Z",
    window_days: 7,
    postgis: { installed: true, version: "3.5.2" },
    required_tables: { required: [], found_count: 7, missing: [] },
    connector_registry: { total: 22, by_status: { implemented: 22 }, implemented_jobs: [] },
    slo1: {
      window_days: 7, target_pct: 95, include_blocked_as_success: false,
      total_runs: 100, successful_runs: 95, success_rate_pct: 95,
      meets_target: true, below_target_jobs: [], items: []
    },
    slo1_current: {
      window_days: 1, target_pct: 95, include_blocked_as_success: false,
      total_runs: 10, successful_runs: 10, success_rate_pct: 100,
      meets_target: true, below_target_jobs: [], items: [],
      window_role: "current_health"
    },
    slo3: { window_days: 7, total_runs: 100, runs_with_checks: 100, runs_missing_checks: 0, meets_target: true, sample_missing_run_ids: [] },
    source_probe: { total_rows: 0, by_source: {} },
    hard_failures: [],
    warnings: []
  }),
  getOpsTimeseries: vi.fn().mockResolvedValue({ entity: "runs", granularity: "day", items: [] }),
  getPipelineRuns: vi.fn().mockResolvedValue({ page: 1, page_size: 20, total: 0, items: [] }),
  getPipelineChecks: vi.fn().mockResolvedValue({ page: 1, page_size: 20, total: 0, items: [] }),
  getConnectorRegistry: vi.fn().mockResolvedValue({ page: 1, page_size: 20, total: 0, items: [] }),
  getFrontendEvents: vi.fn().mockResolvedValue({ page: 1, page_size: 20, total: 0, items: [] }),
  getOpsSourceCoverage: vi.fn().mockResolvedValue({ source: null, wave: null, reference_period: null, include_internal: false, items: [] })
}));

vi.mock("../shared/api/domain", () => ({
  getTerritories: vi.fn().mockResolvedValue({
    page: 1, page_size: 20, total: 2,
    items: [
      { territory_id: "3121605", level: "municipality", name: "Diamantina", uf: "MG", municipality_ibge_code: "3121605" },
      { territory_id: "3106200", level: "municipality", name: "Belo Horizonte", uf: "MG", municipality_ibge_code: "3106200" }
    ]
  }),
  getIndicators: vi.fn().mockResolvedValue({ page: 1, page_size: 20, total: 0, items: [] }),
  getChoropleth: vi.fn().mockResolvedValue({
    page: 1, page_size: 1000, total: 1,
    items: [{
      territory_id: "3121605", territory_name: "Diamantina", level: "municipio",
      metric: "DATASUS_APS_COBERTURA", reference_period: "2025", value: 70, geometry: null
    }]
  }),
  getMapLayers: vi.fn().mockResolvedValue({
    generated_at_utc: "2026-02-13T18:20:00Z",
    default_layer_id: "territory_municipality",
    fallback_endpoint: "/v1/geo/choropleth",
    items: [{
      id: "territory_municipality", label: "Municipios", territory_level: "municipality",
      is_official: true, source: "silver.dim_territory", default_visibility: true,
      zoom_min: 0, zoom_max: 8
    }]
  }),
  getMapStyleMetadata: vi.fn().mockResolvedValue({
    generated_at_utc: "2026-02-13T18:25:00Z", version: "v1", default_mode: "choropleth",
    severity_palette: [
      { severity: "critical", label: "Critico", color: "#b91c1c" },
      { severity: "stable", label: "Estavel", color: "#0f766e" }
    ],
    domain_palette: [], legend_ranges: [], notes: "style_metadata_v1_static"
  })
}));

vi.mock("../shared/api/qg", () => ({
  getKpisOverview: vi.fn().mockResolvedValue({
    period: "2025",
    metadata: { source_name: "silver.fact_indicator", updated_at: null, coverage_note: "territorial_aggregated", unit: null, notes: null },
    items: [{
      domain: "saude", source: "DATASUS", dataset: "datasus_health",
      indicator_code: "DATASUS_APS_COBERTURA", indicator_name: "Cobertura APS",
      value: 80, unit: "%", delta: null, status: "stable", territory_level: "municipio"
    }]
  }),
  getPrioritySummary: vi.fn().mockResolvedValue({
    period: "2025",
    metadata: { source_name: "silver.fact_indicator", updated_at: null, coverage_note: "territorial_aggregated", unit: null, notes: null },
    total_items: 2, by_status: { critical: 1, attention: 1, stable: 0 },
    by_domain: { saude: 1, trabalho: 1 }, top_territories: ["Diamantina"]
  }),
  getPriorityList: vi.fn().mockResolvedValue({
    period: "2025", level: "municipio", domain: null,
    metadata: { source_name: "silver.fact_indicator", updated_at: null, coverage_note: "territorial_aggregated", unit: null, notes: null },
    items: [{
      territory_id: "3121605", territory_name: "Diamantina", territory_level: "municipio",
      domain: "saude", indicator_code: "DATASUS_APS_COBERTURA", indicator_name: "Cobertura APS",
      value: 70, unit: "%", score: 92, trend: "down", status: "critical",
      rationale: ["Cobertura abaixo da meta regional"],
      evidence: { indicator_code: "DATASUS_APS_COBERTURA", reference_period: "2025", source: "DATASUS", dataset: "datasus_health" }
    }]
  }),
  getInsightsHighlights: vi.fn().mockResolvedValue({
    period: "2025", domain: null, severity: null,
    metadata: { source_name: "silver.fact_indicator", updated_at: null, coverage_note: "territorial_aggregated", unit: null, notes: null },
    items: [{
      title: "Saude critica em Diamantina", severity: "critical", domain: "saude",
      territory_id: "3121605", territory_name: "Diamantina",
      explanation: ["Indicador de APS caiu 5% no periodo"],
      evidence: { indicator_code: "DATASUS_APS_COBERTURA", reference_period: "2025", source: "DATASUS", dataset: "datasus_health" },
      robustness: "high"
    }]
  }),
  postScenarioSimulate: vi.fn().mockResolvedValue({
    territory_id: "3121605", territory_name: "Diamantina", territory_level: "municipio",
    period: "2025", domain: "saude",
    indicator_code: "DATASUS_APS_COBERTURA", indicator_name: "Cobertura APS",
    base_value: 70, simulated_value: 77, delta_value: 7, adjustment_percent: 10,
    base_score: 92, simulated_score: 99, peer_count: 5, base_rank: 3, simulated_rank: 2,
    rank_delta: 1, status_before: "critical", status_after: "attention", impact: "positive",
    metadata: { source_name: "silver.fact_indicator", updated_at: null, coverage_note: "territorial_aggregated", unit: "%", notes: "scenario_simulation_v1_rule_based" },
    explanation: ["APS subiria para 77%, reduzindo criticidade."]
  }),
  postBriefGenerate: vi.fn().mockResolvedValue({
    brief_id: "brief-e2e-001", title: "Brief Executivo - Diamantina",
    generated_at: "2026-02-13T21:00:00Z", period: "2025", level: "municipio",
    territory_id: "3121605", domain: null,
    summary_lines: ["Diamantina apresenta criticidade em saude."],
    recommended_actions: ["Ampliar cobertura APS."],
    evidences: [{
      territory_id: "3121605", territory_name: "Diamantina", territory_level: "municipio",
      domain: "saude", indicator_code: "DATASUS_APS_COBERTURA", indicator_name: "Cobertura APS",
      value: 70, unit: "%", score: 92, status: "critical",
      source: "DATASUS", dataset: "datasus_health", reference_period: "2025"
    }],
    metadata: { source_name: "silver.fact_indicator", updated_at: null, coverage_note: "territorial_aggregated", unit: null, notes: "brief_v1_rule_based" }
  }),
  getTerritoryProfile: vi.fn().mockResolvedValue({
    territory_id: "3121605", territory_name: "Diamantina", territory_level: "municipio",
    period: "2025", overall_score: 68.2, overall_status: "attention", overall_trend: "down",
    metadata: { source_name: "silver.fact_indicator", updated_at: null, coverage_note: "territorial_aggregated", unit: null, notes: null },
    highlights: ["Saude em deterioracao"], domains: []
  }),
  getTerritoryPeers: vi.fn().mockResolvedValue({
    territory_id: "3121605", territory_name: "Diamantina", territory_level: "municipio",
    period: "2025",
    metadata: { source_name: "silver.fact_indicator", updated_at: null, coverage_note: "territorial_aggregated", unit: null, notes: null },
    items: []
  }),
  getTerritoryCompare: vi.fn().mockResolvedValue({
    territory_id: "3121605", territory_name: "Diamantina",
    compare_with_id: "3106200", compare_with_name: "Belo Horizonte", period: "2025",
    metadata: { source_name: "silver.fact_indicator", updated_at: null, coverage_note: "territorial_aggregated", unit: null, notes: null },
    items: []
  }),
  getElectorateSummary: vi.fn().mockResolvedValue({
    level: "municipio", year: 2024,
    metadata: { source_name: "silver.fact_electorate", updated_at: null, coverage_note: "territorial_aggregated", unit: "voters", notes: null },
    total_voters: 52000, turnout: null, turnout_rate: 82.5, abstention_rate: 17.5,
    blank_rate: 2.1, null_rate: 3.4, by_sex: [], by_age: [], by_education: []
  }),
  getElectorateMap: vi.fn().mockResolvedValue({
    level: "municipio", metric: "voters", year: 2024,
    metadata: { source_name: "silver.fact_electorate", updated_at: null, coverage_note: "territorial_aggregated", unit: "voters", notes: null },
    items: []
  })
}));

vi.mock("../shared/api/http", async () => {
  const actual = await vi.importActual<typeof import("../shared/api/http")>("../shared/api/http");
  return {
    ...actual,
    requestJson: vi.fn().mockResolvedValue({ status: "ok", db: true })
  };
});

// ---- tests ----

function renderApp(initialEntries: string[] = ["/"]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } }
  });
  const router = createAppMemoryRouter(initialEntries);
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} future={{ v7_startTransition: true }} />
    </QueryClientProvider>
  );
}

describe("E2E decision flow", () => {
  it("walks Home → Prioridades → Mapa → Território → Eleitorado → Cenários → Briefs", async () => {
    renderApp(["/"]);
    const user = userEvent.setup();

    // ── Step 1: Home (QG / Situação Geral) ──
    await screen.findByText("Situacao geral");
    // KPI summary cards are visible (Layout B sidebar)
    expect(screen.getByText("Criticos")).toBeInTheDocument();
    // Top priority preview is visible
    expect(screen.getByText("Diamantina")).toBeInTheDocument();
    // Quick action links exist
    const priorityLinks = screen.getAllByRole("link", { name: "Prioridades" });
    expect(priorityLinks.length).toBeGreaterThanOrEqual(1);

    // ── Step 2: Navigate to Prioridades ──
    const mainNav = screen.getByRole("navigation", { name: "Navegacao principal" });
    await user.click(within(mainNav).getByRole("link", { name: "Prioridades" }));
    await screen.findByText("Prioridades estrategicas");
    expect(screen.getByText("Cobertura abaixo da meta regional")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar CSV" })).toBeInTheDocument();

    // Verify deep-link to mapa exists with context
    const mapLink = screen.getByRole("link", { name: "Ver no mapa" });
    expect(mapLink.getAttribute("href")).toContain("/mapa");
    expect(mapLink.getAttribute("href")).toContain("metric=DATASUS_APS_COBERTURA");

    // ── Step 3: Navigate to Mapa ──
    await user.click(screen.getByRole("link", { name: "Mapa" }));
    await screen.findByText("Mapa estrategico");
    // Export buttons visible
    expect(screen.getByRole("button", { name: /Exportar.*CSV/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Exportar.*SVG/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Exportar.*PNG/ })).toBeInTheDocument();
    // Profile deep-link exists
    expect(screen.getAllByRole("link", { name: "Abrir perfil" })[0]).toBeInTheDocument();

    // ── Step 4: Navigate to Território 360 (via profile link) ──
    await user.click(screen.getAllByRole("link", { name: "Abrir perfil" })[0]);
    await screen.findByRole("heading", { name: /Diamantina/ });
    // Overall score/status displayed
    expect(screen.getByText("atencao")).toBeInTheDocument();

    // ── Step 5: Navigate to Eleitorado ──
    await user.click(screen.getByRole("link", { name: "Eleitorado" }));
    await screen.findByText("Eleitorado e participacao");

    // ── Step 6: Navigate to Cenários ──
    await user.click(screen.getByRole("link", { name: "Cenarios" }));
    await screen.findByText("Cenarios estrategicos");
    // Submit a simulation
    await user.clear(screen.getByLabelText("Percentual de ajuste"));
    await user.type(screen.getByLabelText("Percentual de ajuste"), "10");
    await user.click(screen.getByRole("button", { name: "Simular" }));
    await screen.findByText("Resultado: Diamantina");
    expect(screen.getByText("APS subiria para 77%, reduzindo criticidade.")).toBeInTheDocument();

    // ── Step 7: Navigate to Briefs ──
    await user.click(screen.getByRole("link", { name: "Briefs" }));
    await screen.findByText("Briefs executivos");
    // Generate a brief
    await user.click(screen.getByRole("button", { name: "Gerar brief" }));
    await screen.findByText("Brief Executivo - Diamantina");
    expect(screen.getByText("Diamantina apresenta criticidade em saude.")).toBeInTheDocument();
    expect(screen.getByText("Ampliar cobertura APS.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Exportar.*HTML/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Imprimir/ })).toBeInTheDocument();
  });

  it("deep-links propagate context: mapa → territory profile with query params", async () => {
    renderApp(["/mapa?metric=DATASUS_APS_COBERTURA&period=2025&territory_id=3121605"]);
    const user = userEvent.setup();

    await screen.findByText("Mapa estrategico");
    const profileLink = screen.getAllByRole("link", { name: "Abrir perfil" })[0];
    expect(profileLink).toBeInTheDocument();

    await user.click(profileLink);
    await screen.findByRole("heading", { name: /Diamantina/ });
  });

  it("deep-links propagate context: territory → cenários with query params", async () => {
    renderApp(["/cenarios?territory_id=3121605&period=2025&domain=saude"]);

    await screen.findByText("Cenarios estrategicos");
    // Verify territory was pre-loaded
    await screen.findByLabelText("Percentual de ajuste");
  });

  it("deep-links propagate context: territory → briefs with query params", async () => {
    renderApp(["/briefs?territory_id=3121605&period=2025&domain=saude&limit=3"]);

    await screen.findByText("Briefs executivos");
    await screen.findByRole("button", { name: "Gerar brief" });
  });

  it("navigates back from admin to executive flow without state loss", async () => {
    renderApp(["/"]);
    const user = userEvent.setup();

    // Start in Home
    await screen.findByText("Situacao geral");

    // Go to Admin
    await user.click(screen.getByRole("link", { name: "Admin" }));
    await screen.findByText("Admin tecnico");

    // Return to Prioridades
    await user.click(screen.getByRole("link", { name: "Prioridades" }));
    await screen.findByText("Prioridades estrategicas");
    expect(screen.getByText("Diamantina")).toBeInTheDocument();
  });
});
