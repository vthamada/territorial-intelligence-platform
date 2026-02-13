import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getChoropleth, getMapLayers, getTerritories } from "../../../shared/api/domain";
import { getInsightsHighlights, getKpisOverview, getPriorityList, getPrioritySummary, postBriefGenerate, postScenarioSimulate } from "../../../shared/api/qg";
import { QgBriefsPage } from "./QgBriefsPage";
import { QgInsightsPage } from "./QgInsightsPage";
import { QgMapPage } from "./QgMapPage";
import { QgOverviewPage } from "./QgOverviewPage";
import { QgPrioritiesPage } from "./QgPrioritiesPage";
import { QgScenariosPage } from "./QgScenariosPage";

vi.mock("../../../shared/api/qg", () => ({
  getKpisOverview: vi.fn(),
  getPrioritySummary: vi.fn(),
  getPriorityList: vi.fn(),
  getInsightsHighlights: vi.fn(),
  postScenarioSimulate: vi.fn(),
  postBriefGenerate: vi.fn()
}));

vi.mock("../../../shared/api/domain", () => ({
  getChoropleth: vi.fn(),
  getMapLayers: vi.fn(),
  getTerritories: vi.fn()
}));

function renderWithQueryClient(ui: ReactElement, initialEntries: string[] = ["/"]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0
      }
    }
  });

  return render(
    <MemoryRouter initialEntries={initialEntries} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </MemoryRouter>
  );
}

describe("QG pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(getKpisOverview).mockResolvedValue({
      period: "2025",
      metadata: {
        source_name: "silver.fact_indicator",
        updated_at: null,
        coverage_note: "territorial_aggregated",
        unit: null,
        notes: null
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
    });

    vi.mocked(getPrioritySummary).mockResolvedValue({
      period: "2025",
      metadata: {
        source_name: "silver.fact_indicator",
        updated_at: null,
        coverage_note: "territorial_aggregated",
        unit: null,
        notes: null
      },
      total_items: 3,
      by_status: { critical: 1, attention: 1, stable: 1 },
      by_domain: { saude: 2, trabalho: 1 },
      top_territories: ["Diamantina"]
    });

    vi.mocked(getPriorityList).mockResolvedValue({
      period: "2025",
      level: "municipio",
      domain: null,
      metadata: {
        source_name: "silver.fact_indicator",
        updated_at: null,
        coverage_note: "territorial_aggregated",
        unit: null,
        notes: null
      },
      items: [
        {
          territory_id: "3121605",
          territory_name: "Diamantina",
          territory_level: "municipio",
          domain: "saude",
          indicator_code: "DATASUS_APS_COBERTURA",
          indicator_name: "Cobertura APS",
          value: 70,
          unit: "%",
          score: 92,
          trend: "stable",
          status: "critical",
          rationale: ["Racional critico"],
          evidence: {
            indicator_code: "DATASUS_APS_COBERTURA",
            reference_period: "2025",
            source: "DATASUS",
            dataset: "datasus_health"
          }
        }
      ]
    });

    vi.mocked(getInsightsHighlights).mockResolvedValue({
      period: "2025",
      domain: null,
      severity: null,
      metadata: {
        source_name: "silver.fact_indicator",
        updated_at: null,
        coverage_note: "territorial_aggregated",
        unit: null,
        notes: null
      },
      items: [
        {
          title: "Saude: Diamantina",
          severity: "critical",
          domain: "saude",
          territory_id: "3121605",
          territory_name: "Diamantina",
          explanation: ["Explicacao curta"],
          evidence: {
            indicator_code: "DATASUS_APS_COBERTURA",
            reference_period: "2025",
            source: "DATASUS",
            dataset: "datasus_health"
          },
          robustness: "high"
        }
      ]
    });

    vi.mocked(getChoropleth).mockResolvedValue({
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
          value: 100,
          geometry: null
        }
      ]
    });

    vi.mocked(getMapLayers).mockResolvedValue({
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
        },
        {
          id: "territory_district",
          label: "Distritos",
          territory_level: "district",
          is_official: true,
          source: "silver.dim_territory",
          default_visibility: true,
          zoom_min: 9,
          zoom_max: 11
        }
      ]
    });

    vi.mocked(getTerritories).mockResolvedValue({
      page: 1,
      page_size: 20,
      total: 1,
      items: [
        {
          territory_id: "3121605",
          level: "municipality",
          name: "Diamantina",
          uf: "MG",
          municipality_ibge_code: "3121605"
        }
      ]
    });

    vi.mocked(postScenarioSimulate).mockResolvedValue({
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
        notes: "scenario_simulation_v1_rule_based"
      },
      explanation: ["Ajuste aplicado no indicador de teste."]
    });

    vi.mocked(postBriefGenerate).mockResolvedValue({
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
          reference_period: "2025",
        }
      ],
      metadata: {
        source_name: "silver.fact_indicator",
        updated_at: null,
        coverage_note: "territorial_aggregated",
        unit: null,
        notes: "brief_v1_rule_based"
      }
    });
  });

  it("applies overview filters only on submit", async () => {
    renderWithQueryClient(<QgOverviewPage />);
    await waitFor(() => expect(getKpisOverview).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getPriorityList).toHaveBeenCalledTimes(1));
    await screen.findByLabelText("Periodo");

    await userEvent.type(screen.getByLabelText("Periodo"), "2024");
    await userEvent.selectOptions(screen.getByLabelText("Nivel territorial"), "district");
    expect(getKpisOverview).toHaveBeenCalledTimes(1);
    expect(getPriorityList).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    await waitFor(() => expect(getKpisOverview).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(getPriorityList).toHaveBeenCalledTimes(2));

    expect(vi.mocked(getKpisOverview).mock.calls[1]?.[0]).toMatchObject({
      period: "2024",
      level: "district",
      limit: 20
    });
    expect(vi.mocked(getPriorityList).mock.calls[1]?.[0]).toMatchObject({
      period: "2024",
      level: "district",
      limit: 5
    });
    expect(
      screen
        .getAllByRole("link", { name: "Abrir prioridades" })
        .some((link) => link.getAttribute("href") === "/prioridades")
    ).toBe(true);
    expect(
      screen
        .getAllByRole("link", { name: "Ver no mapa" })
        .some((link) => link.getAttribute("href") === "/mapa?metric=DATASUS_APS_COBERTURA&period=2025&territory_id=3121605")
    ).toBe(true);
    expect(screen.getByRole("link", { name: "Abrir territorio critico" })).toBeInTheDocument();
  });

  it("applies priority filters only on submit", async () => {
    renderWithQueryClient(<QgPrioritiesPage />);
    await waitFor(() => expect(getPriorityList).toHaveBeenCalledTimes(1));
    await screen.findByLabelText("Dominio");

    await userEvent.selectOptions(screen.getByLabelText("Dominio"), "saude");
    await userEvent.selectOptions(screen.getByLabelText("Somente criticos"), "true");
    expect(getPriorityList).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    await waitFor(() => expect(getPriorityList).toHaveBeenCalledTimes(2));

    expect(vi.mocked(getPriorityList).mock.calls[1]?.[0]).toMatchObject({
      domain: "saude",
      level: "municipality",
      limit: 100
    });
    expect(screen.getByText("Racional critico")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar CSV" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver no mapa" })).toHaveAttribute(
      "href",
      "/mapa?metric=DATASUS_APS_COBERTURA&period=2025&territory_id=3121605"
    );
  });

  it("applies choropleth filters only on submit", async () => {
    renderWithQueryClient(<QgMapPage />);
    await waitFor(() => expect(getChoropleth).toHaveBeenCalledTimes(1));
    await screen.findByLabelText("Codigo do indicador");
    expect(screen.getByRole("button", { name: "Exportar SVG" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar PNG" })).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText("Codigo do indicador"));
    await userEvent.type(screen.getByLabelText("Codigo do indicador"), "DATASUS_APS_COBERTURA");
    await userEvent.clear(screen.getByLabelText("Periodo"));
    await userEvent.type(screen.getByLabelText("Periodo"), "2024");
    await userEvent.selectOptions(screen.getByLabelText("Nivel territorial"), "distrito");
    expect(getChoropleth).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    await waitFor(() => expect(getChoropleth).toHaveBeenCalledTimes(2));

    expect(vi.mocked(getChoropleth).mock.calls[1]?.[0]).toMatchObject({
      metric: "DATASUS_APS_COBERTURA",
      period: "2024",
      level: "distrito",
      page: 1,
      page_size: 1000
    });
  });

  it("renders choropleth values when API returns numeric string", async () => {
    vi.mocked(getChoropleth).mockResolvedValueOnce({
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
          value: "100.5" as unknown as number,
          geometry: null
        }
      ]
    });

    renderWithQueryClient(<QgMapPage />);
    await waitFor(() => expect(getChoropleth).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("100,50")).toBeInTheDocument();
  });

  it("applies insights filters only on submit", async () => {
    renderWithQueryClient(<QgInsightsPage />);
    await waitFor(() => expect(getInsightsHighlights).toHaveBeenCalledTimes(1));
    await screen.findByLabelText("Dominio");

    await userEvent.selectOptions(screen.getByLabelText("Dominio"), "saude");
    await userEvent.selectOptions(screen.getByLabelText("Severidade"), "critical");
    expect(getInsightsHighlights).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    await waitFor(() => expect(getInsightsHighlights).toHaveBeenCalledTimes(2));

    expect(vi.mocked(getInsightsHighlights).mock.calls[1]?.[0]).toMatchObject({
      domain: "saude",
      severity: "critical",
      limit: 50
    });
    expect(screen.getByText("Saude: Diamantina")).toBeInTheDocument();
  });

  it("submits scenario simulation and renders result", async () => {
    renderWithQueryClient(<QgScenariosPage />);
    await waitFor(() => expect(getTerritories).toHaveBeenCalledTimes(1));
    await screen.findByLabelText("Percentual de ajuste");

    await userEvent.clear(screen.getByLabelText("Percentual de ajuste"));
    await userEvent.type(screen.getByLabelText("Percentual de ajuste"), "10");
    await userEvent.click(screen.getByRole("button", { name: "Simular" }));

    await waitFor(() => expect(postScenarioSimulate).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Resultado: Diamantina")).toBeInTheDocument();
    expect(screen.getByText("Ajuste aplicado no indicador de teste.")).toBeInTheDocument();
  });

  it("submits brief generation and renders summary", async () => {
    renderWithQueryClient(<QgBriefsPage />);
    await waitFor(() => expect(getTerritories).toHaveBeenCalledTimes(1));
    await screen.findByRole("button", { name: "Gerar brief" });

    await userEvent.click(screen.getByRole("button", { name: "Gerar brief" }));

    await waitFor(() => expect(postBriefGenerate).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Brief Executivo - Diamantina")).toBeInTheDocument();
    expect(screen.getByText("Resumo mock")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar HTML" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Imprimir / PDF" })).toBeInTheDocument();
  });

  it("loads brief filters from URL query params", async () => {
    renderWithQueryClient(<QgBriefsPage />, ["/briefs?territory_id=3121605&period=2024&domain=saude&limit=5"]);
    await waitFor(() => expect(getTerritories).toHaveBeenCalledTimes(1));
    await screen.findByRole("button", { name: "Gerar brief" });

    await userEvent.click(screen.getByRole("button", { name: "Gerar brief" }));

    await waitFor(() => expect(postBriefGenerate).toHaveBeenCalledTimes(1));
    expect(vi.mocked(postBriefGenerate).mock.calls[0]?.[0]).toMatchObject({
      territory_id: "3121605",
      period: "2024",
      domain: "saude",
      limit: 5,
      level: "municipality"
    });
  });

  it("loads map filters from URL query params", async () => {
    renderWithQueryClient(
      <QgMapPage />,
      ["/mapa?metric=DATASUS_APS_COBERTURA&period=2024&level=district&territory_id=3121605"]
    );

    await waitFor(() => expect(getChoropleth).toHaveBeenCalledTimes(1));
    await screen.findByRole("button", { name: "Exportar CSV" });
    expect(vi.mocked(getChoropleth).mock.calls[0]?.[0]).toMatchObject({
      metric: "DATASUS_APS_COBERTURA",
      period: "2024",
      level: "distrito",
      page: 1,
      page_size: 1000
    });
    expect(screen.getByRole("button", { name: "Exportar CSV" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar SVG" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar PNG" })).toBeInTheDocument();
  });

  it("loads priority filters from URL query params", async () => {
    renderWithQueryClient(
      <QgPrioritiesPage />,
      ["/prioridades?period=2024&level=district&domain=saude&only_critical=true&sort=trend_desc"]
    );

    await waitFor(() => expect(getPriorityList).toHaveBeenCalledTimes(1));
    await screen.findByLabelText("Periodo");
    expect(vi.mocked(getPriorityList).mock.calls[0]?.[0]).toMatchObject({
      period: "2024",
      level: "district",
      domain: "saude",
      limit: 100,
    });

    expect((screen.getByLabelText("Periodo") as HTMLInputElement).value).toBe("2024");
    expect((screen.getByLabelText("Nivel territorial") as HTMLSelectElement).value).toBe("district");
    expect((screen.getByLabelText("Dominio") as HTMLSelectElement).value).toBe("saude");
    expect((screen.getByLabelText("Somente criticos") as HTMLSelectElement).value).toBe("true");
    expect((screen.getByLabelText("Ordenar por") as HTMLSelectElement).value).toBe("trend_desc");
  });

  it("loads insights filters from URL query params", async () => {
    renderWithQueryClient(
      <QgInsightsPage />,
      ["/insights?period=2024&domain=saude&severity=critical"]
    );

    await waitFor(() => expect(getInsightsHighlights).toHaveBeenCalledTimes(1));
    await screen.findByLabelText("Periodo");
    expect(vi.mocked(getInsightsHighlights).mock.calls[0]?.[0]).toMatchObject({
      period: "2024",
      domain: "saude",
      severity: "critical",
      limit: 50,
    });

    expect((screen.getByLabelText("Periodo") as HTMLInputElement).value).toBe("2024");
    expect((screen.getByLabelText("Dominio") as HTMLSelectElement).value).toBe("saude");
    expect((screen.getByLabelText("Severidade") as HTMLSelectElement).value).toBe("critical");
  });
});
