import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
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
        <RouterProvider router={router} />
      </QueryClientProvider>
    );

    await screen.findByText("Status geral");

    const user = userEvent.setup();
    await user.click(screen.getByRole("link", { name: "Execucoes" }));
    await screen.findByText("Execucoes de pipeline");

    await user.click(screen.getByRole("link", { name: "Checks" }));
    await screen.findByText("Checks de pipeline");

    await user.click(screen.getByRole("link", { name: "Conectores" }));
    await screen.findByText("Registry de conectores");

    await user.click(screen.getByRole("link", { name: "Territorios e Indicadores" }));
    await screen.findByText("Territorios");
    await screen.findByText("Indicadores");
  });
});
