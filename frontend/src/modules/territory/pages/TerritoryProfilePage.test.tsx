import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getTerritories } from "../../../shared/api/domain";
import { ApiClientError } from "../../../shared/api/http";
import { getTerritoryCompare, getTerritoryPeers, getTerritoryProfile } from "../../../shared/api/qg";
import { TerritoryProfilePage } from "./TerritoryProfilePage";

vi.mock("../../../shared/api/domain", () => ({
  getTerritories: vi.fn()
}));

vi.mock("../../../shared/api/qg", () => ({
  getTerritoryProfile: vi.fn(),
  getTerritoryCompare: vi.fn(),
  getTerritoryPeers: vi.fn()
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0
      }
    }
  });

  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </MemoryRouter>
  );
}

describe("TerritoryProfilePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(getTerritories).mockResolvedValue({
      page: 1,
      page_size: 200,
      total: 2,
      items: [
        {
          territory_id: "3121605",
          level: "municipio",
          name: "Diamantina",
          uf: "MG",
          municipality_ibge_code: "3121605"
        },
        {
          territory_id: "3106200",
          level: "municipio",
          name: "Belo Horizonte",
          uf: "MG",
          municipality_ibge_code: "3106200"
        }
      ]
    });

    vi.mocked(getTerritoryProfile).mockResolvedValue({
      territory_id: "3121605",
      territory_name: "Diamantina",
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
        notes: null
      },
      highlights: ["Destaque teste"],
      domains: [
        {
          domain: "saude",
          status: "stable",
          score: null,
          indicators_count: 1,
          indicators: [
            {
              indicator_code: "DATASUS_APS_COBERTURA",
              indicator_name: "Cobertura APS",
              value: 77.5,
              unit: "%",
              reference_period: "2025",
              status: "stable"
            }
          ]
        }
      ]
    });

    vi.mocked(getTerritoryCompare).mockResolvedValue({
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
        notes: null
      },
      items: [
        {
          domain: "saude",
          indicator_code: "DATASUS_APS_COBERTURA",
          indicator_name: "Cobertura APS",
          unit: "%",
          reference_period: "2025",
          base_value: 77.5,
          compare_value: 70.2,
          delta: 7.3,
          delta_percent: 10.4,
          direction: "up"
        }
      ]
    });

    vi.mocked(getTerritoryPeers).mockResolvedValue({
      territory_id: "3121605",
      territory_name: "Diamantina",
      territory_level: "municipio",
      period: "2025",
      metadata: {
        source_name: "silver.fact_indicator",
        updated_at: null,
        coverage_note: "territorial_aggregated",
        unit: null,
        notes: "territory_peers_v1_similarity_rule_based"
      },
      items: [
        {
          territory_id: "3106200",
          territory_name: "Belo Horizonte",
          territory_level: "municipio",
          similarity_score: 91.7,
          shared_indicators: 2,
          avg_score: 69.5,
          status: "attention"
        }
      ]
    });
  });

  it("loads profile, peers and requests compare after explicit action", async () => {
    renderWithQueryClient(<TerritoryProfilePage />);

    await waitFor(() => expect(getTerritories).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getTerritoryProfile).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getTerritoryPeers).toHaveBeenCalledTimes(1));
    await screen.findByRole("heading", { name: "Status geral do territorio" });
    expect(getTerritoryCompare).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Diamantina" })).toBeInTheDocument();
    expect(screen.getByText("Status geral do territorio")).toBeInTheDocument();
    expect(screen.getByText("74,50")).toBeInTheDocument();
    expect(screen.getByText("Saude")).toBeInTheDocument();
    expect(screen.getByText("Pares recomendados")).toBeInTheDocument();
    expect(screen.getAllByText("Belo Horizonte").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Gerar brief deste territorio" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Simular cenarios" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Comparar" }));

    await waitFor(() => expect(getTerritoryCompare).toHaveBeenCalledTimes(1));
    expect(vi.mocked(getTerritoryCompare).mock.calls[0]?.[0]).toBe("3121605");
    expect(vi.mocked(getTerritoryCompare).mock.calls[0]?.[1]).toMatchObject({
      with_id: "3106200",
      limit: 80
    });
    expect(screen.getByText("Comparacao territorial")).toBeInTheDocument();
  });

  it("keeps profile visible when peers endpoint fails", async () => {
    vi.mocked(getTerritoryPeers).mockRejectedValueOnce(new Error("Peers unavailable"));

    renderWithQueryClient(<TerritoryProfilePage />);

    await waitFor(() => expect(getTerritories).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getTerritoryProfile).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getTerritoryPeers).toHaveBeenCalledTimes(1));

    expect(screen.getByRole("heading", { name: "Status geral do territorio" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Diamantina" })).toBeInTheDocument();
    expect(screen.getByText("Falha ao carregar pares recomendados")).toBeInTheDocument();
  });

  it("renders empty state instead of hard error on profile 404", async () => {
    vi.mocked(getTerritoryProfile).mockRejectedValueOnce(
      new ApiClientError("No indicators found for selected territory", 404)
    );

    renderWithQueryClient(<TerritoryProfilePage />);

    await waitFor(() => expect(getTerritories).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getTerritoryProfile).toHaveBeenCalledTimes(1));

    await screen.findByText("Sem dados para o territorio selecionado");
    expect(
      screen.getByText("Nao ha indicadores disponiveis para esse recorte. Selecione outro territorio ou periodo.")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Territorio base")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aplicar filtros" })).toBeInTheDocument();
  });

  it("shows empty highlights state when profile has no highlights", async () => {
    vi.mocked(getTerritoryProfile).mockResolvedValueOnce({
      territory_id: "3121605",
      territory_name: "Diamantina",
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
        notes: null,
      },
      highlights: [],
      domains: [
        {
          domain: "saude",
          status: "stable",
          score: null,
          indicators_count: 1,
          indicators: [
            {
              indicator_code: "DATASUS_APS_COBERTURA",
              indicator_name: "Cobertura APS",
              value: 77.5,
              unit: "%",
              reference_period: "2025",
              status: "stable",
            },
          ],
        },
      ],
    });

    renderWithQueryClient(<TerritoryProfilePage />);

    await waitFor(() => expect(getTerritories).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getTerritoryProfile).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("Sem destaques no recorte")).toBeInTheDocument();
    expect(
      screen.getByText("Nao ha destaques narrativos para o territorio e periodo selecionados."),
    ).toBeInTheDocument();
  });
});
