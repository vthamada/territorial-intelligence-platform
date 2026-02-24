import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiClientError } from "../../../shared/api/http";
import { getMapLayers, getMapLayersCoverage } from "../../../shared/api/domain";
import { getOpsReadiness } from "../../../shared/api/ops";
import { AdminHubPage } from "./AdminHubPage";

vi.mock("../../../shared/api/ops", () => ({
  getOpsReadiness: vi.fn(),
}));

vi.mock("../../../shared/api/domain", () => ({
  getMapLayers: vi.fn(),
  getMapLayersCoverage: vi.fn(),
}));

function renderWithQueryClient() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <QueryClientProvider client={queryClient}>
        <AdminHubPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("AdminHubPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(getOpsReadiness).mockResolvedValue({
      status: "READY",
      strict: false,
      generated_at_utc: "2026-02-23T10:00:00Z",
      window_days: 7,
      postgis: {
        installed: true,
        version: "3.5.2",
      },
      required_tables: {
        required: [],
        found_count: 7,
        missing: [],
      },
      connector_registry: {
        total: 29,
        by_status: { implemented: 27, partial: 2 },
        implemented_jobs: ["sidra_indicators_fetch"],
      },
      slo1: {
        window_days: 7,
        target_pct: 95,
        include_blocked_as_success: false,
        total_runs: 10,
        successful_runs: 9,
        success_rate_pct: 90,
        meets_target: false,
        below_target_jobs: ["quality_suite"],
        items: [],
      },
      slo1_current: {
        window_days: 1,
        target_pct: 95,
        include_blocked_as_success: false,
        total_runs: 2,
        successful_runs: 2,
        success_rate_pct: 100,
        meets_target: true,
        below_target_jobs: [],
        items: [],
        window_role: "current_health",
      },
      slo3: {
        window_days: 7,
        total_runs: 10,
        runs_with_checks: 10,
        runs_missing_checks: 0,
        meets_target: true,
        sample_missing_run_ids: [],
      },
      source_probe: {
        total_rows: 0,
        by_source: {},
      },
      hard_failures: [],
      warnings: ["SLO-1 below target"],
    });

    vi.mocked(getMapLayers).mockResolvedValue({
      generated_at_utc: "2026-02-23T10:00:00Z",
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
          zoom_max: 8,
        },
      ],
    });

    vi.mocked(getMapLayersCoverage).mockResolvedValue({
      generated_at_utc: "2026-02-23T10:00:00Z",
      metric: null,
      period: null,
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
      ],
    });
  });

  it("shows request_id and allows retry when readiness fails", async () => {
    vi.mocked(getOpsReadiness).mockRejectedValueOnce(
      new ApiClientError("Readiness indisponivel", 503, "req-readiness-001"),
    );

    renderWithQueryClient();

    expect(await screen.findByText("Falha ao carregar readiness")).toBeInTheDocument();
    expect(screen.getByText("Readiness indisponivel")).toBeInTheDocument();
    expect(screen.getByText("request_id: req-readiness-001")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(getOpsReadiness).toHaveBeenCalledTimes(2));
  });

  it("shows request_id and allows retry when layer coverage fails", async () => {
    vi.mocked(getMapLayersCoverage).mockRejectedValueOnce(
      new ApiClientError("Cobertura indisponivel", 503, "req-coverage-001"),
    );

    renderWithQueryClient();

    expect(await screen.findByText("Falha ao carregar cobertura das camadas")).toBeInTheDocument();
    expect(screen.getByText("Cobertura indisponivel")).toBeInTheDocument();
    expect(screen.getByText("request_id: req-coverage-001")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(getMapLayersCoverage).toHaveBeenCalledTimes(2));
  });
});
