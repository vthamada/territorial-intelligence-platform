import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
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
    expect(screen.getByText("12000")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Ano"), "2022");
    await userEvent.selectOptions(screen.getByLabelText("Metrica do mapa"), "abstention_rate");
    expect(getElectorateMap).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await waitFor(() => expect(getElectorateMap).toHaveBeenCalledTimes(2));
    expect(vi.mocked(getElectorateSummary).mock.calls[1]?.[0]).toMatchObject({
      level: "municipality",
      year: 2022
    });
    expect(vi.mocked(getElectorateMap).mock.calls[1]?.[0]).toMatchObject({
      level: "municipality",
      year: 2022,
      metric: "abstention_rate",
      include_geometry: false,
      limit: 500
    });
  });
});
