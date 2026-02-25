import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { createAppMemoryRouter } from "./router";

vi.mock("../shared/api/ops", () => ({
  getOpsSummary: vi.fn().mockResolvedValue({
    runs: { total: 1, by_status: { success: 1 }, by_wave: { "MVP-1": 1 }, latest_started_at_utc: null },
    checks: { total: 1, by_status: { pass: 1 }, latest_created_at_utc: null },
    connectors: { total: 1, by_status: { implemented: 1 }, by_wave: { "MVP-1": 1 }, latest_updated_at_utc: null }
  }),
  getOpsSla: vi.fn().mockResolvedValue({
    include_blocked_as_success: false,
    min_total_runs: 1,
    items: []
  }),
  getOpsReadiness: vi.fn().mockResolvedValue({
    status: "READY",
    strict: false,
    generated_at_utc: "2026-02-12T20:30:00Z",
    window_days: 7,
    postgis: { installed: true, version: "3.5.2" },
    required_tables: { required: [], found_count: 7, missing: [] },
    connector_registry: { total: 1, by_status: { implemented: 1 }, implemented_jobs: ["sidra_indicators_fetch"] },
    slo1: {
      window_days: 7,
      target_pct: 95,
      include_blocked_as_success: false,
      total_runs: 1,
      successful_runs: 1,
      success_rate_pct: 100,
      meets_target: true,
      below_target_jobs: [],
      items: []
    },
    slo1_current: {
      window_days: 1,
      target_pct: 95,
      include_blocked_as_success: false,
      total_runs: 1,
      successful_runs: 1,
      success_rate_pct: 100,
      meets_target: true,
      below_target_jobs: [],
      items: [],
      window_role: "current_health"
    },
    slo3: { window_days: 7, total_runs: 1, runs_with_checks: 1, runs_missing_checks: 0, meets_target: true, sample_missing_run_ids: [] },
    source_probe: { total_rows: 0, by_source: {} },
    hard_failures: [],
    warnings: []
  }),
  getOpsTimeseries: vi.fn().mockResolvedValue({
    entity: "runs",
    granularity: "day",
    items: []
  }),
  getPipelineRuns: vi.fn().mockResolvedValue({
    page: 1,
    page_size: 20,
    total: 0,
    items: []
  }),
  getPipelineChecks: vi.fn().mockResolvedValue({
    page: 1,
    page_size: 20,
    total: 0,
    items: []
  }),
  getConnectorRegistry: vi.fn().mockResolvedValue({
    page: 1,
    page_size: 20,
    total: 0,
    items: []
  }),
  getFrontendEvents: vi.fn().mockResolvedValue({
    page: 1,
    page_size: 20,
    total: 0,
    items: []
  }),
  getOpsSourceCoverage: vi.fn().mockResolvedValue({
    source: null,
    wave: null,
    reference_period: null,
    include_internal: false,
    items: []
  })
}));

vi.mock("../shared/api/domain", () => ({
  getTerritories: vi.fn().mockResolvedValue({
    page: 1,
    page_size: 20,
    total: 0,
    items: []
  }),
  getIndicators: vi.fn().mockResolvedValue({
    page: 1,
    page_size: 20,
    total: 0,
    items: []
  }),
  getChoropleth: vi.fn().mockResolvedValue({
    page: 1,
    page_size: 1000,
    total: 1,
    items: [
      {
        territory_id: "3121605",
        territory_name: "Diamantina",
        level: "municipio",
        metric: "MTE_NOVO_CAGED_SALDO_TOTAL",
        reference_period: "2025",
        value: 120,
        geometry: null
      }
    ]
  }),
  getMapLayers: vi.fn().mockResolvedValue({
    generated_at_utc: "2026-02-13T18:20:00Z",
    default_layer_id: "territory_municipality",
    fallback_endpoint: "/v1/geo/choropleth",
    items: [
      {
        id: "territory_municipality",
        label: "Municipios",
        territory_level: "municipality",
        is_official: true,
        source: "silver.dim_territory",
        default_visibility: true,
        zoom_min: 0,
        zoom_max: 8
      }
    ]
  }),
  getMapStyleMetadata: vi.fn().mockResolvedValue({
    generated_at_utc: "2026-02-13T18:25:00Z",
    version: "v1",
    default_mode: "choropleth",
    severity_palette: [
      { severity: "critical", label: "Critico", color: "#b91c1c" },
      { severity: "attention", label: "Atencao", color: "#d97706" },
      { severity: "stable", label: "Estavel", color: "#0f766e" }
    ],
    domain_palette: [],
    legend_ranges: [],
    notes: "style_metadata_v1_static"
  })
}));

vi.mock("../shared/api/qg", () => ({
  getKpisOverview: vi.fn().mockResolvedValue({
    period: "2025",
    metadata: {
      source_name: "silver.fact_indicator",
      updated_at: null,
      coverage_note: "territorial_aggregated",
      unit: null,
      notes: "mock"
    },
    items: [
      {
        domain: "saude",
        source: "DATASUS",
        dataset: "datasus_health",
        indicator_code: "DATASUS_APS_COBERTURA",
        indicator_name: "Cobertura APS",
        value: 80,
        unit: "%",
        delta: null,
        status: "stable",
        territory_level: "municipio"
      }
    ]
  }),
  getPrioritySummary: vi.fn().mockResolvedValue({
    period: "2025",
    metadata: {
      source_name: "silver.fact_indicator",
      updated_at: null,
      coverage_note: "territorial_aggregated",
      unit: null,
      notes: "mock"
    },
    total_items: 1,
    by_status: { critical: 0, attention: 1, stable: 0 },
    by_domain: { saude: 1 },
    top_territories: ["Diamantina"]
  }),
  getPriorityList: vi.fn().mockResolvedValue({
    period: "2025",
    level: "municipio",
    domain: null,
    metadata: {
      source_name: "silver.fact_indicator",
      updated_at: null,
      coverage_note: "territorial_aggregated",
      unit: null,
      notes: "mock"
    },
    items: [
      {
        territory_id: "3121605",
        territory_name: "Diamantina",
        territory_level: "municipio",
        domain: "saude",
        indicator_code: "DATASUS_APS_COBERTURA",
        indicator_name: "Cobertura APS",
        value: 80,
        unit: "%",
        score: 90,
        trend: "stable",
        status: "critical",
        rationale: ["Item critico de teste"],
        evidence: {
          indicator_code: "DATASUS_APS_COBERTURA",
          reference_period: "2025",
          source: "DATASUS",
          dataset: "datasus_health"
        }
      }
    ]
  }),
  getInsightsHighlights: vi.fn().mockResolvedValue({
    period: "2025",
    domain: null,
    severity: null,
    metadata: {
      source_name: "silver.fact_indicator",
      updated_at: null,
      coverage_note: "territorial_aggregated",
      unit: null,
      notes: "mock"
    },
    items: []
  }),
  postScenarioSimulate: vi.fn().mockResolvedValue({
    territory_id: "3121605",
    territory_name: "Diamantina",
    territory_level: "municipio",
    period: "2025",
    domain: "saude",
    indicator_code: "DATASUS_APS_COBERTURA",
    indicator_name: "Cobertura APS",
    base_value: 70,
    simulated_value: 77,
    delta_value: 7,
    adjustment_percent: 10,
    base_score: 90,
    simulated_score: 99,
    peer_count: 10,
    base_rank: 3,
    simulated_rank: 2,
    rank_delta: 1,
    status_before: "critical",
    status_after: "critical",
    impact: "unchanged",
    metadata: {
      source_name: "silver.fact_indicator",
      updated_at: null,
      coverage_note: "territorial_aggregated",
      unit: "%",
      notes: "mock"
    },
    explanation: ["mock"]
  }),
  postBriefGenerate: vi.fn().mockResolvedValue({
    brief_id: "brief-mock-001",
    title: "Brief Executivo - Diamantina",
    generated_at: "2026-02-11T12:00:00Z",
    period: "2025",
    level: "municipio",
    territory_id: "3121605",
    domain: null,
    summary_lines: ["Resumo mock"],
    recommended_actions: ["Acao mock"],
    evidences: [
      {
        territory_id: "3121605",
        territory_name: "Diamantina",
        territory_level: "municipio",
        domain: "saude",
        indicator_code: "DATASUS_APS_COBERTURA",
        indicator_name: "Cobertura APS",
        value: 70,
        unit: "%",
        score: 90,
        status: "critical",
        source: "DATASUS",
        dataset: "datasus_health",
        reference_period: "2025"
      }
    ],
    metadata: {
      source_name: "silver.fact_indicator",
      updated_at: null,
      coverage_note: "territorial_aggregated",
      unit: null,
      notes: "mock"
    }
  }),
  getTerritoryProfile: vi.fn().mockResolvedValue({
    territory_id: "3106200",
    territory_name: "Belo Horizonte",
    territory_level: "municipio",
    period: "2025",
    overall_score: 74.5,
    overall_status: "attention",
    overall_trend: "up",
    metadata: {
      source_name: "silver.fact_indicator",
      updated_at: null,
      coverage_note: "territorial_aggregated",
      unit: null,
      notes: "mock"
    },
    highlights: ["Destaque de teste"],
    domains: []
  }),
  getTerritoryPeers: vi.fn().mockResolvedValue({
    territory_id: "3106200",
    territory_name: "Belo Horizonte",
    territory_level: "municipio",
    period: "2025",
    metadata: {
      source_name: "silver.fact_indicator",
      updated_at: null,
      coverage_note: "territorial_aggregated",
      unit: null,
      notes: "mock"
    },
    items: []
  }),
  getTerritoryCompare: vi.fn().mockResolvedValue({
    territory_id: "3121605",
    territory_name: "Diamantina",
    compare_with_id: "3106200",
    compare_with_name: "Belo Horizonte",
    period: "2025",
    metadata: {
      source_name: "silver.fact_indicator",
      updated_at: null,
      coverage_note: "territorial_aggregated",
      unit: null,
      notes: "mock"
    },
    items: []
  }),
  getElectorateSummary: vi.fn().mockResolvedValue({
    level: "municipio",
    year: 2024,
    metadata: {
      source_name: "silver.fact_electorate",
      updated_at: null,
      coverage_note: "territorial_aggregated",
      unit: "voters",
      notes: "mock"
    },
    total_voters: 1000,
    turnout: null,
    turnout_rate: 80,
    abstention_rate: 20,
    blank_rate: 2,
    null_rate: 3,
    by_sex: [],
    by_age: [],
    by_education: []
  }),
  getElectorateMap: vi.fn().mockResolvedValue({
    level: "municipio",
    metric: "voters",
    year: 2024,
    metadata: {
      source_name: "silver.fact_electorate",
      updated_at: null,
      coverage_note: "territorial_aggregated",
      unit: "voters",
      notes: "mock"
    },
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

describe("Router smoke", () => {
  it("navigates across core routes without crashing", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          gcTime: 0
        }
      }
    });
    const router = createAppMemoryRouter(["/"]);

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} future={{ v7_startTransition: true }} />
      </QueryClientProvider>
    );

    await screen.findByText("Situacao geral");

    const user = userEvent.setup();
    const mainNav = screen.getByRole("navigation", { name: "Navegacao principal" });
    await user.click(within(mainNav).getByRole("link", { name: "Prioridades" }));
    await screen.findByText("Prioridades estrategicas");

    await user.click(screen.getByRole("link", { name: "Mapa" }));
    await screen.findByLabelText("Buscar territorio");
    await user.click(screen.getAllByRole("link", { name: "Abrir perfil" })[0]);
    await screen.findByText("Belo Horizonte");

    await user.click(screen.getByRole("link", { name: "Insights" }));
    await screen.findByText("Insights estrategicos");

    await user.click(screen.getByRole("link", { name: "Cenarios" }));
    await screen.findByText("Cenarios estrategicos");

    await user.click(screen.getByRole("link", { name: "Briefs" }));
    await screen.findByText("Briefs executivos");

    await user.click(screen.getByRole("link", { name: "Territorio 360" }));
    await screen.findByText("Perfil 360 do territorio");

    await user.click(screen.getByRole("link", { name: "Eleitorado" }));
    await screen.findByText("Eleitorado e participacao");

    await user.click(screen.getByRole("link", { name: "Admin" }));
    await screen.findByText("Admin tecnico");

    await user.click(screen.getByRole("link", { name: "Abrir Saude Ops" }));
    await screen.findByText("Status geral");

    await user.click(screen.getByRole("link", { name: "Admin" }));
    await screen.findByText("Admin tecnico");
    await user.click(screen.getByRole("link", { name: "Abrir Execucoes" }));
    await screen.findByText("Execucoes de pipeline");

    await user.click(screen.getByRole("link", { name: "Admin" }));
    await screen.findByText("Admin tecnico");
    await user.click(screen.getByRole("link", { name: "Abrir Checks" }));
    await screen.findByText("Checks de pipeline");

    await user.click(screen.getByRole("link", { name: "Admin" }));
    await screen.findByText("Admin tecnico");
    await user.click(screen.getByRole("link", { name: "Abrir Conectores" }));
    await screen.findByText("Registry de conectores");

    await user.click(screen.getByRole("link", { name: "Admin" }));
    await screen.findByText("Admin tecnico");
    await user.click(screen.getByRole("link", { name: "Abrir Eventos Frontend" }));
    await screen.findByText("Eventos frontend");

    await user.click(screen.getByRole("link", { name: "Admin" }));
    await screen.findByText("Admin tecnico");
    await user.click(screen.getByRole("link", { name: "Abrir Territorios e Indicadores" }));
    await screen.findByText("Territorios");
    await screen.findByText("Indicadores");
  });
});
