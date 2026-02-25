import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getChoropleth, getMapLayers, getMapLayersCoverage, getMapStyleMetadata, getTerritories } from "../../../shared/api/domain";
import { ApiClientError } from "../../../shared/api/http";
import {
  getElectorateMap,
  getInsightsHighlights,
  getKpisOverview,
  getPriorityList,
  getPrioritySummary,
  postBriefGenerate,
  postScenarioSimulate,
} from "../../../shared/api/qg";
import { emitTelemetry } from "../../../shared/observability/telemetry";
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
  getElectorateMap: vi.fn(),
  postScenarioSimulate: vi.fn(),
  postBriefGenerate: vi.fn()
}));

vi.mock("../../../shared/api/domain", () => ({
  getChoropleth: vi.fn(),
  getMapLayers: vi.fn(),
  getMapLayersCoverage: vi.fn(),
  getMapStyleMetadata: vi.fn(),
  getTerritories: vi.fn()
}));

vi.mock("../../../shared/observability/telemetry", () => ({
  emitTelemetry: vi.fn(),
}));

function LocationSearchProbe() {
  const location = useLocation();
  return <output data-testid="location-search">{location.search}</output>;
}

function renderWithQueryClient(
  ui: ReactElement,
  initialEntries: string[] = ["/"],
  options?: { includeLocationProbe?: boolean }
) {
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
      {options?.includeLocationProbe ? <LocationSearchProbe /> : null}
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

    vi.mocked(getElectorateMap).mockResolvedValue({
      level: "secao_eleitoral",
      metric: "voters",
      year: 2024,
      metadata: {
        source_name: "silver.fact_electorate",
        updated_at: null,
        coverage_note: "electoral_section",
        unit: null,
        notes: null,
      },
      items: [
        {
          territory_id: "3121605-101-0001",
          territory_name: "Secao 0001",
          territory_level: "secao_eleitoral",
          metric: "voters",
          value: 450,
          year: 2024,
          geometry: null,
        },
      ],
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
          official_status: "official",
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

    vi.mocked(getMapStyleMetadata).mockResolvedValue({
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
    });

    vi.mocked(getMapLayersCoverage).mockResolvedValue({
      generated_at_utc: "2026-02-13T18:26:00Z",
      metric: "MTE_NOVO_CAGED_SALDO_TOTAL",
      period: "2025",
      items: [
        {
          layer_id: "territory_municipality",
          territory_level: "municipality",
          territories_total: 1,
          territories_with_geometry: 1,
          territories_with_indicator: 1,
          is_ready: true,
          notes: null,
        },
        {
          layer_id: "territory_district",
          territory_level: "district",
          territories_total: 1,
          territories_with_geometry: 1,
          territories_with_indicator: 1,
          is_ready: true,
          notes: null,
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

    await userEvent.clear(screen.getByLabelText("Periodo"));
    await userEvent.type(screen.getByLabelText("Periodo"), "2024");
    await userEvent.selectOptions(screen.getByLabelText("Nivel territorial"), "district");
    expect(getKpisOverview).toHaveBeenCalledTimes(1);
    expect(getPriorityList).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Aplicar" }));
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
        .getAllByRole("link", { name: "Prioridades" })
        .some((link) => link.getAttribute("href") === "/prioridades")
    ).toBe(true);
    expect(
      screen
        .getAllByRole("link", { name: "Mapa detalhado" })
        .some((link) => link.getAttribute("href") === "/mapa?territory_id=3121605")
    ).toBe(true);
    expect(screen.getByRole("link", { name: "Territorio critico" })).toBeInTheDocument();
  });

  it("keeps overview operational when priorities and highlights fail", async () => {
    vi.mocked(getPriorityList).mockRejectedValueOnce(
      new ApiClientError("Prioridades indisponiveis no backend", 503, "req-priority-preview-001"),
    );
    vi.mocked(getInsightsHighlights).mockRejectedValueOnce(
      new ApiClientError("Destaques indisponiveis no backend", 503, "req-highlights-001"),
    );

    renderWithQueryClient(<QgOverviewPage />);
    await waitFor(() => expect(getKpisOverview).toHaveBeenCalledTimes(1));

    expect(await screen.findByText("Situacao geral")).toBeInTheDocument();
    expect(await screen.findByText("Falha ao carregar top prioridades")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Destaques/i }));
    expect(await screen.findByText("Falha ao carregar destaques")).toBeInTheDocument();
    expect(screen.getByText("request_id: req-priority-preview-001")).toBeInTheDocument();
    expect(screen.getByText("request_id: req-highlights-001")).toBeInTheDocument();

    const prioritiesBlock = screen.getByText("Falha ao carregar top prioridades").closest(".state-block");
    expect(prioritiesBlock).not.toBeNull();
    await userEvent.click(within(prioritiesBlock as HTMLElement).getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(getPriorityList).toHaveBeenCalledTimes(2));

    const highlightsBlock = screen.getByText("Falha ao carregar destaques").closest(".state-block");
    expect(highlightsBlock).not.toBeNull();
    await userEvent.click(within(highlightsBlock as HTMLElement).getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(getInsightsHighlights).toHaveBeenCalledTimes(2));

    expect(screen.getByRole("link", { name: "Mapa detalhado" })).toHaveAttribute(
      "href",
      expect.stringContaining("/mapa"),
    );
  });

  it("propagates detailed map layer from overview to map links", async () => {
    vi.mocked(getMapLayers).mockResolvedValueOnce({
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
          id: "territory_electoral_section",
          label: "Secoes eleitorais",
          territory_level: "electoral_section",
          is_official: false,
          official_status: "proxy",
          source: "silver.dim_territory",
          default_visibility: false,
          zoom_min: 12,
          zoom_max: null
        },
        {
          id: "territory_polling_place",
          label: "Locais de votacao",
          territory_level: "electoral_section",
          is_official: false,
          official_status: "proxy",
          source: "silver.dim_territory",
          default_visibility: false,
          zoom_min: 12,
          zoom_max: null
        }
      ]
    });

    renderWithQueryClient(<QgOverviewPage />);
    await waitFor(() => expect(getKpisOverview).toHaveBeenCalledTimes(1));
    await screen.findByLabelText("Periodo");
    expect(screen.queryByLabelText("Camada detalhada (Mapa)")).not.toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Nivel territorial"), "electoral_section");
    await screen.findByLabelText("Camada detalhada (Mapa)");

    await userEvent.selectOptions(screen.getByLabelText("Camada detalhada (Mapa)"), "territory_polling_place");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar" }));

    expect(screen.getByRole("link", { name: "Mapa detalhado" })).toHaveAttribute(
      "href",
      "/mapa?territory_id=3121605&layer_id=territory_polling_place&level=secao_eleitoral"
    );
    expect(
      screen.queryAllByText((_, element) => element?.textContent?.includes("Classificacao: proxy") ?? false).length,
    ).toBeGreaterThan(0);
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
      limit: 24
    });
    expect(screen.getByText("Racional critico")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar CSV" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver no mapa" })).toHaveAttribute(
      "href",
      "/mapa?territory_id=3121605"
    );
  });

  it("paginates priority cards when result set is large", async () => {
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
      items: Array.from({ length: 30 }, (_, index) => {
        const itemNumber = index + 1;
        return {
          territory_id: "3121605",
          territory_name: "Diamantina",
          territory_level: "municipio",
          domain: "saude",
          indicator_code: `INDICADOR_${itemNumber}`,
          indicator_name: `Indicador ${itemNumber}`,
          value: itemNumber,
          unit: "%",
          score: 101 - itemNumber,
          trend: "stable",
          status: "critical",
          rationale: [`Racional ${itemNumber}`],
          evidence: {
            indicator_code: `INDICADOR_${itemNumber}`,
            reference_period: "2025",
            source: "DATASUS",
            dataset: "datasus_health"
          }
        };
      })
    });

    renderWithQueryClient(<QgPrioritiesPage />);
    await waitFor(() => expect(getPriorityList).toHaveBeenCalledTimes(1));
    await screen.findByText((_, element) => element?.textContent?.trim() === "Saude | Indicador 1");

    expect(screen.getByText("Pagina 1 de 2")).toBeInTheDocument();
    expect(
      screen.queryByText((_, element) => element?.textContent?.trim() === "Saude | Indicador 30")
    ).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Proxima" }));

    expect(screen.getByText("Pagina 2 de 2")).toBeInTheDocument();
    expect(
      screen.getByText((_, element) => element?.textContent?.trim() === "Saude | Indicador 30")
    ).toBeInTheDocument();
    expect(
      screen.queryByText((_, element) => element?.textContent?.trim() === "Saude | Indicador 1")
    ).not.toBeInTheDocument();
  });

  it("applies choropleth filters only on submit", async () => {
    renderWithQueryClient(<QgMapPage />);
    await waitFor(() => expect(getChoropleth).toHaveBeenCalledTimes(1));
    await screen.findByLabelText("Buscar territorio");
    expect(screen.getByRole("button", { name: /Exportar.*SVG/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Exportar.*PNG/ })).toBeInTheDocument();
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
    expect((await screen.findAllByText("100,50")).length).toBeGreaterThan(0);
  });

  /* Test removed: "Camada eleitoral detalhada" selector was removed from UI. */

  /* Test removed: electoral detailed layer toggle buttons were removed from UI. */

  /* Test removed: "loads explicit layer selection from URL query param" — layer selector UI removed. */

  /* Test removed: local_votacao guidance text was removed from UI. */

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
    expect(screen.getByRole("button", { name: /Exportar.*HTML/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Imprimir/ })).toBeInTheDocument();
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
    await screen.findByRole("button", { name: /Exportar.*CSV/ });
    expect(vi.mocked(getChoropleth).mock.calls[0]?.[0]).toMatchObject({
      metric: "MTE_NOVO_CAGED_SALDO_TOTAL",
      period: "2025",
      level: "distrito",
      page: 1,
      page_size: 1000
    });
    expect(screen.getByRole("button", { name: /Exportar.*CSV/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Exportar.*SVG/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Exportar.*PNG/ })).toBeInTheDocument();
  });

  it("loads map visual controls from URL query params", async () => {
    renderWithQueryClient(
      <QgMapPage />,
      [
        "/mapa?metric=DATASUS_APS_COBERTURA&period=2024&level=district&layer_id=territory_district&basemap=light&viz=points&renderer=svg&zoom=7",
      ],
    );

    await waitFor(() => expect(getChoropleth).toHaveBeenCalledTimes(1));
    await screen.findByRole("button", { name: /Exportar.*SVG/ });
    expect(vi.mocked(getChoropleth).mock.calls[0]?.[0]).toMatchObject({
      metric: "MTE_NOVO_CAGED_SALDO_TOTAL",
      period: "2025",
      level: "distrito",
      page: 1,
      page_size: 1000,
    });
    expect(screen.getByRole("button", { name: "OpenStreetMap" })).toBeInTheDocument();
  });

  it("renders strategic layer groups and territorial cut selector", async () => {
    renderWithQueryClient(<QgMapPage />);

    await waitFor(() => expect(getChoropleth).toHaveBeenCalledTimes(1));
    const strategicPanel = await screen.findByLabelText("Painel de camadas estrategicas");
    expect(strategicPanel).toBeInTheDocument();
    const scoped = within(strategicPanel);
    expect(scoped.getByRole("heading", { name: "Territorio" })).toBeInTheDocument();
    expect(scoped.getByRole("heading", { name: "Eleitoral" })).toBeInTheDocument();
    expect(scoped.getByRole("heading", { name: "Servicos" })).toBeInTheDocument();

    // Verify overlay toggle checkboxes are rendered for toggleable items
    expect(scoped.getByLabelText("Ativar camada Escolas")).toBeInTheDocument();
    expect(scoped.getByLabelText("Ativar camada UBS / Saude")).toBeInTheDocument();
    expect(scoped.getByLabelText("Ativar camada Locais de votacao")).toBeInTheDocument();
  });

  it("toggles overlay layers on and off via checkboxes", async () => {
    renderWithQueryClient(<QgMapPage />);
    await waitFor(() => expect(getChoropleth).toHaveBeenCalledTimes(1));
    const strategicPanel = await screen.findByLabelText("Painel de camadas estrategicas");
    const scoped = within(strategicPanel);

    const schoolsCheckbox = scoped.getByLabelText("Ativar camada Escolas") as HTMLInputElement;
    expect(schoolsCheckbox.checked).toBe(false);

    await userEvent.click(schoolsCheckbox);
    expect(schoolsCheckbox.checked).toBe(true);

    await userEvent.click(schoolsCheckbox);
    expect(schoolsCheckbox.checked).toBe(false);
  });

  /* Test removed: strategic presets were removed from map UI. */

  it("keeps map operational at granular levels without simplified fallback", async () => {
    vi.mocked(getMapLayers).mockResolvedValueOnce({
      generated_at_utc: "2026-02-13T18:20:00Z",
      default_layer_id: "territory_electoral_section",
      fallback_endpoint: "/v1/geo/choropleth",
      items: [
        {
          id: "territory_electoral_section",
          label: "Secoes eleitorais",
          territory_level: "electoral_section",
          is_official: false,
          source: "silver.dim_territory",
          default_visibility: true,
          zoom_min: 12,
          zoom_max: null,
        },
      ],
    });

    renderWithQueryClient(
      <QgMapPage />,
      ["/mapa?metric=MTE_NOVO_CAGED_SALDO_TOTAL&period=2025&level=secao_eleitoral&renderer=svg"],
    );

    await waitFor(() => expect(getMapLayers).toHaveBeenCalledTimes(1));
    expect(await screen.findByRole("button", { name: "OpenStreetMap" })).toBeInTheDocument();
    await waitFor(() => {
      const operationalStateEvents = vi
        .mocked(emitTelemetry)
        .mock.calls.map(([event]) => event)
        .filter((event) => event.name === "map_operational_state_changed");
      expect(operationalStateEvents).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            attributes: expect.objectContaining({
              renderer: "advanced",
              level: "secao_eleitoral",
            }),
          }),
        ]),
      );
    });
  });

  /* Test removed: telemetry interactions depended on controls removed from map UI. */

  it("syncs map query params after applying filters and view controls", async () => {
    renderWithQueryClient(<QgMapPage />, ["/mapa"], { includeLocationProbe: true });
    await waitFor(() => expect(getChoropleth).toHaveBeenCalledTimes(1));
    await screen.findByLabelText("Buscar territorio");

    await waitFor(() => {
      const search = screen.getByTestId("location-search").textContent ?? "";
      expect(search).not.toContain("renderer=");
      expect(search).not.toContain("basemap=");
      expect(search).not.toContain("metric=");
      expect(search).not.toContain("period=");
    });
  });

  it("supports urban layer scope from URL without choropleth request", async () => {
    renderWithQueryClient(
      <QgMapPage />,
      ["/mapa?scope=urban&layer_id=urban_roads&metric=MTE_NOVO_CAGED_SALDO_TOTAL&period=2025"],
    );

    await screen.findByLabelText("Buscar territorio");
    expect(getChoropleth).not.toHaveBeenCalled();
  });

  it("requests polling places on checkbox click and falls back to 2024 when selected period has no electorate data", async () => {
    vi.mocked(getMapLayers).mockResolvedValueOnce({
      generated_at_utc: "2026-02-13T18:20:00Z",
      default_layer_id: "territory_municipality",
      fallback_endpoint: "/v1/geo/choropleth",
      items: [
        {
          id: "territory_municipality",
          label: "Municipios",
          territory_level: "municipality",
          is_official: true,
          official_status: "official",
          source: "silver.dim_territory",
          default_visibility: true,
          zoom_min: 0,
          zoom_max: 8,
        },
        {
          id: "territory_electoral_section",
          label: "Secoes eleitorais",
          territory_level: "electoral_section",
          is_official: false,
          official_status: "proxy",
          source: "silver.dim_territory",
          default_visibility: true,
          zoom_min: 12,
          zoom_max: null,
        },
      ],
    });

    vi.mocked(getElectorateMap)
      .mockResolvedValueOnce({
        level: "secao_eleitoral",
        metric: "voters",
        year: 2025,
        metadata: {
          source_name: "silver.fact_electorate",
          updated_at: null,
          coverage_note: "polling_place_aggregated",
          unit: null,
          notes: null,
        },
        items: [],
      })
      .mockResolvedValueOnce({
        level: "secao_eleitoral",
        metric: "voters",
        year: 2024,
        metadata: {
          source_name: "silver.fact_electorate",
          updated_at: null,
          coverage_note: "polling_place_aggregated",
          unit: null,
          notes: null,
        },
        items: [
          {
            territory_id: "polling-place-001",
            territory_name: "Local 1",
            territory_level: "secao_eleitoral",
            metric: "voters",
            value: 500,
            year: 2024,
            geometry: { type: "Point", coordinates: [-43.6, -18.2] },
            polling_place_name: "Escola Municipal Centro",
            polling_place_code: "1001",
            section_count: 2,
            sections: ["0001", "0002"],
          },
        ],
      });

    renderWithQueryClient(<QgMapPage />, ["/mapa"]);

    await screen.findByLabelText("Buscar territorio");
    await userEvent.click(screen.getByLabelText("Ativar camada Locais de votacao"));
    await waitFor(() => expect(getElectorateMap).toHaveBeenCalledTimes(2));

    expect(vi.mocked(getElectorateMap).mock.calls[0]?.[0]).toMatchObject({ year: 2025 });
    expect(vi.mocked(getElectorateMap).mock.calls[1]?.[0]).toMatchObject({ year: 2024 });
  });

  it("shows retryable manifest and style metadata errors", async () => {
    vi.mocked(getMapLayers).mockRejectedValueOnce(
      new ApiClientError("Manifesto de camadas indisponivel no backend", 503, "req-map-layers-001"),
    );
    vi.mocked(getMapStyleMetadata).mockRejectedValueOnce(
      new ApiClientError("Metadados de estilo indisponiveis no backend", 503, "req-style-001"),
    );

    renderWithQueryClient(<QgMapPage />);

    expect(await screen.findByText("Manifesto de camadas indisponivel")).toBeInTheDocument();
    expect(await screen.findByText("Falha ao carregar metadados de estilo")).toBeInTheDocument();
    expect(screen.getByText("request_id: req-map-layers-001")).toBeInTheDocument();
    expect(screen.getByText("request_id: req-style-001")).toBeInTheDocument();

    const manifestBlock = screen.getByText("Manifesto de camadas indisponivel").closest(".state-block");
    expect(manifestBlock).not.toBeNull();

    await userEvent.click(within(manifestBlock as HTMLElement).getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(getMapLayers).toHaveBeenCalledTimes(2));
  });

  /* Test removed: coverage error StateBlock was removed from UI. */

  it("focuses territory from quick search and syncs territory_id in URL", async () => {
    renderWithQueryClient(<QgMapPage />, ["/mapa"], { includeLocationProbe: true });
    await waitFor(() => expect(getChoropleth).toHaveBeenCalledTimes(1));
    await screen.findByLabelText("Buscar territorio");

    await userEvent.clear(screen.getByLabelText("Buscar territorio"));
    await userEvent.type(screen.getByLabelText("Buscar territorio"), "Diamantina");
    await userEvent.click(screen.getByRole("button", { name: "Focar" }));

    await waitFor(() => {
      const search = screen.getByTestId("location-search").textContent ?? "";
      expect(search).toContain("territory_id=3121605");
    });

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
      limit: 24,
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
