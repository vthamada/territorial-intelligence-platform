import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiClientError } from "../../../shared/api/http";
import { getMapLayers, getMapLayersCoverage } from "../../../shared/api/domain";
import { getAdminSyncHistory, getAdminSyncStatus, getOpsReadiness, startAdminSync } from "../../../shared/api/ops";
import { AdminHubPage } from "./AdminHubPage";

vi.mock("../../../shared/api/ops", () => ({
  getAdminSyncHistory: vi.fn(),
  getAdminSyncStatus: vi.fn(),
  getOpsReadiness: vi.fn(),
  startAdminSync: vi.fn(),
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

    vi.mocked(getAdminSyncStatus).mockResolvedValue({ job: null });
    vi.mocked(getAdminSyncHistory).mockResolvedValue({
      page: 1,
      page_size: 10,
      total: 0,
      items: [],
    });
    vi.mocked(startAdminSync).mockResolvedValue({
      job_id: "job-001",
      mode: "validate",
      status: "queued",
      started_at_utc: "2026-03-12T13:00:00Z",
      finished_at_utc: null,
      is_active: true,
      current_step: "export_data_coverage_scorecard",
      last_message: "Job enfileirado.",
      recent_logs: ["Job enfileirado."],
      steps: [
        {
          name: "export_data_coverage_scorecard",
          status: "pending",
          started_at_utc: null,
          finished_at_utc: null,
          exit_code: null,
          summary: null,
        },
      ],
    });

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
          label: "Municípios",
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
      new ApiClientError("Readiness indisponível", 503, "req-readiness-001"),
    );

    renderWithQueryClient();

    expect(await screen.findByText("Falha ao carregar readiness")).toBeInTheDocument();
    expect(screen.getByText("Readiness indisponível")).toBeInTheDocument();
    expect(screen.getByText("request_id: req-readiness-001")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(getOpsReadiness).toHaveBeenCalledTimes(2));
  });

  it("shows request_id and allows retry when layer coverage fails", async () => {
    vi.mocked(getMapLayersCoverage).mockRejectedValueOnce(
      new ApiClientError("Cobertura indisponível", 503, "req-coverage-001"),
    );

    renderWithQueryClient();

    expect(await screen.findByText("Falha ao carregar cobertura das camadas")).toBeInTheDocument();
    expect(screen.getByText("Cobertura indisponível")).toBeInTheDocument();
    expect(screen.getByText("request_id: req-coverage-001")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(getMapLayersCoverage).toHaveBeenCalledTimes(2));
  });

  it("shows empty state and empty persisted history when no admin sync job exists", async () => {
    renderWithQueryClient();

    expect(await screen.findByText("Nenhuma execução administrativa registrada")).toBeInTheDocument();
    expect(await screen.findByText("Sem histórico persistido")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Validar ambiente" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sincronizar ambiente" })).toBeInTheDocument();
  });

  it("starts validation with the official payload", async () => {
    renderWithQueryClient();

    await screen.findByText("Nenhuma execução administrativa registrada");
    await userEvent.click(screen.getByRole("button", { name: "Validar ambiente" }));

    await waitFor(() => expect(startAdminSync).toHaveBeenCalledTimes(1));
    expect(vi.mocked(startAdminSync).mock.calls[0]?.[0]).toEqual({
      mode: "validate",
      include_wave7: true,
      allow_backfill_blocked: true,
    });
  });

  it("starts sync only after confirmation", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    renderWithQueryClient();

    await screen.findByText("Nenhuma execução administrativa registrada");
    await userEvent.click(screen.getByRole("button", { name: "Sincronizar ambiente" }));

    await waitFor(() => expect(startAdminSync).toHaveBeenCalledTimes(1));
    expect(vi.mocked(startAdminSync).mock.calls[0]?.[0]).toEqual({
      mode: "sync",
      include_wave7: true,
      allow_backfill_blocked: true,
    });

    confirmSpy.mockRestore();
  });

  it("shows explicit admin-sync upgrade message when backend returns 404", async () => {
    vi.mocked(getAdminSyncStatus).mockRejectedValueOnce(
      new ApiClientError("Request failed with status 404", 404, "req-admin-404"),
    );

    renderWithQueryClient();

    expect(await screen.findByText("Falha ao carregar status da operação assistida")).toBeInTheDocument();
    expect(screen.getByText("Backend sem suporte à operação assistida. Atualize e reinicie a API.")).toBeInTheDocument();
    expect(screen.getByText("request_id: req-admin-404")).toBeInTheDocument();
  });
});
