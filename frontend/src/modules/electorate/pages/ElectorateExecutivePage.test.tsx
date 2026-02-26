import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getElectorateMap, getElectorateSummary } from "../../../shared/api/qg";
import { ElectorateExecutivePage } from "./ElectorateExecutivePage";

vi.mock("../../../shared/api/qg", () => ({
  getElectorateSummary: vi.fn(),
  getElectorateMap: vi.fn()
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

describe("ElectorateExecutivePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(getElectorateSummary).mockResolvedValue({
      level: "municipio",
      year: 2024,
      metadata: {
        source_name: "silver.fact_electorate",
        updated_at: null,
        coverage_note: "territorial_aggregated",
        unit: "voters",
        notes: null
      },
      total_voters: 12000,
      turnout: 8000,
      turnout_rate: 80,
      abstention_rate: 20,
      blank_rate: 2,
      null_rate: 3,
      by_sex: [{ label: "MASCULINO", voters: 5800, share_percent: 48.3 }],
      by_age: [],
      by_education: []
    });

    vi.mocked(getElectorateMap).mockResolvedValue({
      level: "municipio",
      metric: "voters",
      year: 2024,
      metadata: {
        source_name: "silver.fact_electorate",
        updated_at: null,
        coverage_note: "territorial_aggregated",
        unit: "voters",
        notes: null
      },
      items: [
        {
          territory_id: "3121605",
          territory_name: "Diamantina",
          territory_level: "municipio",
          metric: "voters",
          value: 12000,
          year: 2024,
          geometry: null
        }
      ]
    });
  });

  it("applies electorate filters only on submit", async () => {
    renderWithQueryClient(<ElectorateExecutivePage />);

    await waitFor(() => expect(getElectorateSummary).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getElectorateMap).toHaveBeenCalledTimes(1));
    expect(screen.getAllByText("12.000").length).toBeGreaterThan(0);

    await userEvent.type(screen.getByLabelText("Ano"), "2022");
    await userEvent.selectOptions(screen.getByLabelText("Metrica do mapa"), "abstention_rate");
    expect(getElectorateMap).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await waitFor(() => expect(getElectorateSummary).toHaveBeenCalledTimes(3));
    await waitFor(() => expect(getElectorateMap).toHaveBeenCalledTimes(3));

    expect(vi.mocked(getElectorateSummary).mock.calls).toContainEqual([
      expect.objectContaining({
        level: "municipality",
        year: 2022
      })
    ]);
    expect(vi.mocked(getElectorateSummary).mock.calls).toContainEqual([
      expect.objectContaining({
        level: "municipality"
      })
    ]);
    expect(vi.mocked(getElectorateMap).mock.calls).toContainEqual([
      expect.objectContaining({
        level: "municipality",
        year: 2022,
        metric: "abstention_rate",
        include_geometry: false,
        limit: 500
      })
    ]);
    expect(vi.mocked(getElectorateMap).mock.calls).toContainEqual([
      expect.objectContaining({
        level: "municipality",
        metric: "abstention_rate",
        include_geometry: false,
        limit: 500
      })
    ]);
  });

  it("falls back to latest available year when selected year has no electorate data", async () => {
    vi.mocked(getElectorateSummary)
      .mockResolvedValueOnce({
        level: "municipio",
        year: 2024,
        metadata: {
          source_name: "silver.fact_electorate",
          updated_at: null,
          coverage_note: "territorial_aggregated",
          unit: "voters",
          notes: null
        },
        total_voters: 12000,
        turnout: 8000,
        turnout_rate: 80,
        abstention_rate: 20,
        blank_rate: 2,
        null_rate: 3,
        by_sex: [{ label: "MASCULINO", voters: 5800, share_percent: 48.3 }],
        by_age: [],
        by_education: []
      })
      .mockResolvedValueOnce({
        level: "municipio",
        year: null,
        metadata: {
          source_name: "silver.fact_electorate",
          updated_at: null,
          coverage_note: "territorial_aggregated",
          unit: "voters",
          notes: null
        },
        total_voters: 0,
        turnout: 0,
        turnout_rate: null,
        abstention_rate: null,
        blank_rate: null,
        null_rate: null,
        by_sex: [],
        by_age: [],
        by_education: []
      })
      .mockResolvedValueOnce({
        level: "municipio",
        year: 2024,
        metadata: {
          source_name: "silver.fact_electorate",
          updated_at: null,
          coverage_note: "territorial_aggregated",
          unit: "voters",
          notes: null
        },
        total_voters: 12000,
        turnout: 8000,
        turnout_rate: 80,
        abstention_rate: 20,
        blank_rate: 2,
        null_rate: 3,
        by_sex: [{ label: "MASCULINO", voters: 5800, share_percent: 48.3 }],
        by_age: [],
        by_education: []
      });

    vi.mocked(getElectorateMap)
      .mockResolvedValueOnce({
        level: "municipio",
        metric: "voters",
        year: 2024,
        metadata: {
          source_name: "silver.fact_electorate",
          updated_at: null,
          coverage_note: "territorial_aggregated",
          unit: "voters",
          notes: null
        },
        items: [
          {
            territory_id: "3121605",
            territory_name: "Diamantina",
            territory_level: "municipio",
            metric: "voters",
            value: 12000,
            year: 2024,
            geometry: null
          }
        ]
      })
      .mockResolvedValueOnce({
        level: "municipio",
        metric: "voters",
        year: null,
        metadata: {
          source_name: "silver.fact_electorate",
          updated_at: null,
          coverage_note: "territorial_aggregated",
          unit: "voters",
          notes: null
        },
        items: []
      })
      .mockResolvedValueOnce({
        level: "municipio",
        metric: "voters",
        year: 2024,
        metadata: {
          source_name: "silver.fact_electorate",
          updated_at: null,
          coverage_note: "territorial_aggregated",
          unit: "voters",
          notes: null
        },
        items: [
          {
            territory_id: "3121605",
            territory_name: "Diamantina",
            territory_level: "municipio",
            metric: "voters",
            value: 12000,
            year: 2024,
            geometry: null
          }
        ]
      });

    renderWithQueryClient(<ElectorateExecutivePage />);

    await waitFor(() => expect(getElectorateSummary).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getElectorateMap).toHaveBeenCalledTimes(1));

    await userEvent.clear(screen.getByLabelText("Ano"));
    await userEvent.type(screen.getByLabelText("Ano"), "2022");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await screen.findByText("Ano 2022 sem dados consolidados");
    expect(screen.getAllByText("12.000").length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Mostrando automaticamente o ultimo recorte com dados \(2024\) para manter a leitura executiva\./)
    ).toBeInTheDocument();
    expect(screen.queryByText("Sem dados para o ano informado")).not.toBeInTheDocument();
    expect(screen.getByText("MASCULINO")).toBeInTheDocument();
  });

  it("does not break when fallback queries fail but selected year has data", async () => {
    let summaryUndefinedCalls = 0;
    let mapUndefinedCalls = 0;

    vi.mocked(getElectorateSummary).mockImplementation(async (params) => {
      const year = params?.year;
      if (year === 2022) {
        return {
          level: "municipio",
          year: 2022,
          metadata: {
            source_name: "silver.fact_electorate",
            updated_at: null,
            coverage_note: "territorial_aggregated",
            unit: "voters",
            notes: null,
          },
          total_voters: 15000,
          turnout: 11000,
          turnout_rate: 73.3,
          abstention_rate: 26.7,
          blank_rate: 1.8,
          null_rate: 2.2,
          by_sex: [{ label: "MASCULINO", voters: 7200, share_percent: 48 }],
          by_age: [],
          by_education: [],
        };
      }

      summaryUndefinedCalls += 1;
      if (summaryUndefinedCalls >= 2) {
        throw new Error("Fallback summary unavailable");
      }

      return {
        level: "municipio",
        year: 2024,
        metadata: {
          source_name: "silver.fact_electorate",
          updated_at: null,
          coverage_note: "territorial_aggregated",
          unit: "voters",
          notes: null,
        },
        total_voters: 12000,
        turnout: 8000,
        turnout_rate: 80,
        abstention_rate: 20,
        blank_rate: 2,
        null_rate: 3,
        by_sex: [{ label: "MASCULINO", voters: 5800, share_percent: 48.3 }],
        by_age: [],
        by_education: [],
      };
    });

    vi.mocked(getElectorateMap).mockImplementation(async (params) => {
      const year = params?.year;
      const metric = (params?.metric ?? "voters") as "voters" | "turnout" | "abstention_rate" | "blank_rate" | "null_rate";
      if (year === 2022) {
        return {
          level: "municipio",
          metric,
          year: 2022,
          metadata: {
            source_name: "silver.fact_electorate",
            updated_at: null,
            coverage_note: "territorial_aggregated",
            unit: "voters",
            notes: null,
          },
          items: [
            {
              territory_id: "3121605",
              territory_name: "Diamantina",
              territory_level: "municipio",
              metric,
              value: metric === "voters" ? 15000 : 26.7,
              year: 2022,
              geometry: null,
            },
          ],
        };
      }

      mapUndefinedCalls += 1;
      if (mapUndefinedCalls >= 2) {
        throw new Error("Fallback map unavailable");
      }

      return {
        level: "municipio",
        metric,
        year: 2024,
        metadata: {
          source_name: "silver.fact_electorate",
          updated_at: null,
          coverage_note: "territorial_aggregated",
          unit: "voters",
          notes: null,
        },
        items: [
          {
            territory_id: "3121605",
            territory_name: "Diamantina",
            territory_level: "municipio",
            metric,
            value: metric === "voters" ? 12000 : 20,
            year: 2024,
            geometry: null,
          },
        ],
      };
    });

    renderWithQueryClient(<ElectorateExecutivePage />);

    await waitFor(() => expect(getElectorateSummary).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getElectorateMap).toHaveBeenCalledTimes(1));

    await userEvent.clear(screen.getByLabelText("Ano"));
    await userEvent.type(screen.getByLabelText("Ano"), "2022");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await waitFor(() => {
      expect(vi.mocked(getElectorateSummary).mock.calls).toContainEqual([
        expect.objectContaining({ level: "municipality", year: 2022 }),
      ]);
    });

    expect((await screen.findAllByText("2022")).length).toBeGreaterThan(0);
    expect(screen.queryByText("Falha ao carregar fallback do eleitorado")).not.toBeInTheDocument();
    expect(screen.getAllByText("15.000").length).toBeGreaterThan(0);
  });

  it("shows fallback error when selected year has no data and fallback fails", async () => {
    let summaryUndefinedCalls = 0;
    let mapUndefinedCalls = 0;

    vi.mocked(getElectorateSummary).mockImplementation(async (params) => {
      const year = params?.year;
      if (year === 2022) {
        return {
          level: "municipio",
          year: null,
          metadata: {
            source_name: "silver.fact_electorate",
            updated_at: null,
            coverage_note: "territorial_aggregated",
            unit: "voters",
            notes: null,
          },
          total_voters: 0,
          turnout: 0,
          turnout_rate: null,
          abstention_rate: null,
          blank_rate: null,
          null_rate: null,
          by_sex: [],
          by_age: [],
          by_education: [],
        };
      }

      summaryUndefinedCalls += 1;
      if (summaryUndefinedCalls >= 2) {
        throw new Error("Fallback summary unavailable");
      }

      return {
        level: "municipio",
        year: 2024,
        metadata: {
          source_name: "silver.fact_electorate",
          updated_at: null,
          coverage_note: "territorial_aggregated",
          unit: "voters",
          notes: null,
        },
        total_voters: 12000,
        turnout: 8000,
        turnout_rate: 80,
        abstention_rate: 20,
        blank_rate: 2,
        null_rate: 3,
        by_sex: [{ label: "MASCULINO", voters: 5800, share_percent: 48.3 }],
        by_age: [],
        by_education: [],
      };
    });

    vi.mocked(getElectorateMap).mockImplementation(async (params) => {
      const year = params?.year;
      const metric = (params?.metric ?? "voters") as "voters" | "turnout" | "abstention_rate" | "blank_rate" | "null_rate";
      if (year === 2022) {
        return {
          level: "municipio",
          metric,
          year: null,
          metadata: {
            source_name: "silver.fact_electorate",
            updated_at: null,
            coverage_note: "territorial_aggregated",
            unit: "voters",
            notes: null,
          },
          items: [],
        };
      }

      mapUndefinedCalls += 1;
      if (mapUndefinedCalls >= 2) {
        throw new Error("Fallback map unavailable");
      }

      return {
        level: "municipio",
        metric,
        year: 2024,
        metadata: {
          source_name: "silver.fact_electorate",
          updated_at: null,
          coverage_note: "territorial_aggregated",
          unit: "voters",
          notes: null,
        },
        items: [
          {
            territory_id: "3121605",
            territory_name: "Diamantina",
            territory_level: "municipio",
            metric,
            value: metric === "voters" ? 12000 : 20,
            year: 2024,
            geometry: null,
          },
        ],
      };
    });

    renderWithQueryClient(<ElectorateExecutivePage />);

    await waitFor(() => expect(getElectorateSummary).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getElectorateMap).toHaveBeenCalledTimes(1));

    await userEvent.clear(screen.getByLabelText("Ano"));
    await userEvent.type(screen.getByLabelText("Ano"), "2022");
    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    expect(await screen.findByText("Falha ao carregar fallback do eleitorado")).toBeInTheDocument();
  });
});
