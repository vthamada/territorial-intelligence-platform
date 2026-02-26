import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getIndicators, getTerritories } from "../../../shared/api/domain";
import { TerritoryIndicatorsPage } from "./TerritoryIndicatorsPage";

vi.mock("../../../shared/api/domain", () => ({
  getTerritories: vi.fn(),
  getIndicators: vi.fn()
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

describe("TerritoryIndicatorsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getTerritories).mockResolvedValue({
      page: 1,
      page_size: 20,
      total: 1,
      items: [
        {
          territory_id: "t-1",
          level: "municipality",
          name: "Diamantina",
          uf: "MG",
          municipality_ibge_code: "3121605"
        }
      ]
    });
    vi.mocked(getIndicators).mockResolvedValue({
      page: 1,
      page_size: 20,
      total: 0,
      items: []
    });
  });

  it("applies indicator filters only when submit is triggered", async () => {
    renderWithQueryClient(<TerritoryIndicatorsPage />);
    await waitFor(() => expect(getIndicators).toHaveBeenCalledTimes(1));

    await userEvent.type(screen.getByLabelText("Codigo indicador"), "POPULACAO_ESTIMADA");
    await userEvent.type(screen.getByLabelText("Fonte"), "IBGE");
    expect(getIndicators).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Selecionar" }));
    await userEvent.click(screen.getByRole("button", { name: "Filtrar" }));

    await waitFor(() => expect(getIndicators).toHaveBeenCalledTimes(2));
    expect(vi.mocked(getIndicators).mock.calls[1]?.[0]).toMatchObject({
      territory_id: "t-1",
      indicator_code: "POPULACAO_ESTIMADA",
      source: "IBGE",
      page: 1,
      page_size: 20
    });
  });

  it("applies territory level filter only when submit is triggered", async () => {
    renderWithQueryClient(<TerritoryIndicatorsPage />);
    await waitFor(() => expect(getTerritories).toHaveBeenCalledTimes(1));

    await userEvent.selectOptions(screen.getByLabelText(/N[ií]vel/i), "district");
    expect(getTerritories).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getAllByRole("button", { name: "Aplicar filtros" })[0]!);
    await waitFor(() => expect(getTerritories).toHaveBeenCalledTimes(2));

    expect(vi.mocked(getTerritories).mock.calls[1]?.[0]).toMatchObject({
      level: "district",
      page: 1,
      page_size: 20
    });
  });
});
