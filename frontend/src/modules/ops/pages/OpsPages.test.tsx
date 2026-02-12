import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { OpsChecksPage } from "./OpsChecksPage";
import { OpsConnectorsPage } from "./OpsConnectorsPage";
import { OpsFrontendEventsPage } from "./OpsFrontendEventsPage";
import { OpsHealthPage } from "./OpsHealthPage";
import { OpsRunsPage } from "./OpsRunsPage";
import { OpsSourceCoveragePage } from "./OpsSourceCoveragePage";
import {
  getConnectorRegistry,
  getFrontendEvents,
  getOpsReadiness,
  getOpsSla,
  getOpsSourceCoverage,
  getOpsSummary,
  getOpsTimeseries,
  getPipelineChecks,
  getPipelineRuns
} from "../../../shared/api/ops";

vi.mock("../../../shared/api/ops", () => ({
  getPipelineRuns: vi.fn(),
  getPipelineChecks: vi.fn(),
  getConnectorRegistry: vi.fn(),
  getFrontendEvents: vi.fn(),
  getOpsSourceCoverage: vi.fn(),
  getOpsSummary: vi.fn(),
  getOpsSla: vi.fn(),
  getOpsReadiness: vi.fn(),
  getOpsTimeseries: vi.fn()
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

describe("Ops pages filters", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: "ok", db: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
    );
    vi.mocked(getPipelineRuns).mockResolvedValue({
      page: 1,
      page_size: 20,
      total: 0,
      items: []
    });
    vi.mocked(getPipelineChecks).mockResolvedValue({
      page: 1,
      page_size: 20,
      total: 0,
      items: []
    });
    vi.mocked(getConnectorRegistry).mockResolvedValue({
      page: 1,
      page_size: 20,
      total: 0,
      items: []
    });
    vi.mocked(getFrontendEvents).mockResolvedValue({
      page: 1,
      page_size: 20,
      total: 0,
      items: []
    });
    vi.mocked(getOpsSourceCoverage).mockResolvedValue({
      source: null,
      wave: null,
      reference_period: null,
      include_internal: false,
      items: []
    });
    vi.mocked(getOpsSummary).mockResolvedValue({
      runs: { total: 2, by_status: { success: 2 }, by_wave: { "MVP-4": 2 }, latest_started_at_utc: null },
      checks: { total: 2, by_status: { pass: 2 }, latest_created_at_utc: null },
      connectors: { total: 22, by_status: { implemented: 22 }, by_wave: { "MVP-5": 5 }, latest_updated_at_utc: null }
    });
    vi.mocked(getOpsSla).mockResolvedValue({
      include_blocked_as_success: false,
      min_total_runs: 1,
      items: [
        {
          job_name: "sidra_indicators_fetch",
          source: "SIDRA",
          dataset: "sidra_indicators_catalog",
          wave: "MVP-4",
          total_runs: 2,
          successful_runs: 2,
          success_rate: 1,
          p95_duration_seconds: 0.9,
          avg_duration_seconds: 0.7,
          latest_started_at_utc: null
        }
      ]
    });
    vi.mocked(getOpsReadiness).mockResolvedValue({
      status: "READY",
      strict: false,
      generated_at_utc: "2026-02-12T20:30:00Z",
      window_days: 7,
      postgis: {
        installed: true,
        version: "3.5.2"
      },
      required_tables: {
        required: [],
        found_count: 7,
        missing: []
      },
      connector_registry: {
        total: 22,
        by_status: { implemented: 22 },
        implemented_jobs: ["sidra_indicators_fetch"]
      },
      slo1: {
        window_days: 7,
        target_pct: 95,
        include_blocked_as_success: false,
        total_runs: 10,
        successful_runs: 8,
        success_rate_pct: 80,
        meets_target: false,
        below_target_jobs: ["labor_mte_fetch"],
        items: []
      },
      slo1_current: {
        window_days: 1,
        target_pct: 95,
        include_blocked_as_success: false,
        total_runs: 3,
        successful_runs: 3,
        success_rate_pct: 100,
        meets_target: true,
        below_target_jobs: [],
        items: [],
        window_role: "current_health"
      },
      slo3: {
        window_days: 7,
        total_runs: 10,
        runs_with_checks: 10,
        runs_missing_checks: 0,
        meets_target: true,
        sample_missing_run_ids: []
      },
      source_probe: {
        total_rows: 0,
        by_source: {}
      },
      hard_failures: [],
      warnings: ["SLO-1 below target in historical window."]
    });
    vi.mocked(getOpsTimeseries).mockResolvedValue({
      entity: "runs",
      granularity: "day",
      items: []
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("applies runs filters only when submitting form", async () => {
    renderWithQueryClient(<OpsRunsPage />);
    await waitFor(() => expect(getPipelineRuns).toHaveBeenCalledTimes(1));

    await userEvent.type(screen.getByLabelText("Job"), "labor_mte_fetch");
    expect(getPipelineRuns).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    await waitFor(() => expect(getPipelineRuns).toHaveBeenCalledTimes(2));

    expect(vi.mocked(getPipelineRuns).mock.calls[1]?.[0]).toMatchObject({
      job_name: "labor_mte_fetch",
      run_status: undefined,
      page: 1,
      page_size: 20
    });
  });

  it("applies checks filters only when submitting form", async () => {
    renderWithQueryClient(<OpsChecksPage />);
    await waitFor(() => expect(getPipelineChecks).toHaveBeenCalledTimes(1));

    await userEvent.type(screen.getByLabelText("Check"), "mte_data_source_resolved");
    expect(getPipelineChecks).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    await waitFor(() => expect(getPipelineChecks).toHaveBeenCalledTimes(2));

    expect(vi.mocked(getPipelineChecks).mock.calls[1]?.[0]).toMatchObject({
      check_name: "mte_data_source_resolved",
      page: 1,
      page_size: 20
    });
  });

  it("applies connectors filters only when submitting form", async () => {
    renderWithQueryClient(<OpsConnectorsPage />);
    await waitFor(() => expect(getConnectorRegistry).toHaveBeenCalledTimes(1));

    await userEvent.type(screen.getByLabelText("Conector"), "labor_mte_fetch");
    expect(getConnectorRegistry).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    await waitFor(() => expect(getConnectorRegistry).toHaveBeenCalledTimes(2));

    expect(vi.mocked(getConnectorRegistry).mock.calls[1]?.[0]).toMatchObject({
      connector_name: "labor_mte_fetch",
      page: 1,
      page_size: 20
    });
  });

  it("applies frontend events filters only when submitting form", async () => {
    renderWithQueryClient(<OpsFrontendEventsPage />);
    await waitFor(() => expect(getFrontendEvents).toHaveBeenCalledTimes(1));

    await userEvent.selectOptions(screen.getByLabelText("Categoria"), "api_request");
    await userEvent.selectOptions(screen.getByLabelText("Severidade"), "error");
    await userEvent.type(screen.getByLabelText("Evento"), "api_request_failed");
    expect(getFrontendEvents).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    await waitFor(() => expect(getFrontendEvents).toHaveBeenCalledTimes(2));

    expect(vi.mocked(getFrontendEvents).mock.calls[1]?.[0]).toMatchObject({
      category: "api_request",
      severity: "error",
      name: "api_request_failed",
      page: 1,
      page_size: 20
    });
  });

  it("applies source coverage filters only when submitting form", async () => {
    renderWithQueryClient(<OpsSourceCoveragePage />);
    await waitFor(() => expect(getOpsSourceCoverage).toHaveBeenCalledTimes(1));

    await userEvent.type(screen.getByLabelText("Fonte"), "MTE");
    await userEvent.selectOptions(screen.getByLabelText("Wave"), "MVP-3");
    expect(getOpsSourceCoverage).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    await waitFor(() => expect(getOpsSourceCoverage).toHaveBeenCalledTimes(2));

    expect(vi.mocked(getOpsSourceCoverage).mock.calls[1]?.[0]).toMatchObject({
      source: "MTE",
      wave: "MVP-3",
      include_internal: false
    });
  });

  it("loads health page with historical and current SLO windows", async () => {
    renderWithQueryClient(<OpsHealthPage />);

    await waitFor(() => expect(getOpsSummary).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getOpsSla).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getOpsReadiness).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getOpsTimeseries).toHaveBeenCalledTimes(1));

    expect(screen.getByText("Monitor SLO-1")).toBeInTheDocument();
    expect(screen.getByText("SLO-1 (7d)")).toBeInTheDocument();
    expect(screen.getByText("SLO-1 (1d)")).toBeInTheDocument();
    expect(screen.getByText("Status readiness")).toBeInTheDocument();
    expect(screen.getByText("READY")).toBeInTheDocument();

    const slaCall = vi.mocked(getOpsSla).mock.calls[0]?.[0];
    const readinessCall = vi.mocked(getOpsReadiness).mock.calls[0]?.[0];
    expect(slaCall).toMatchObject({ min_total_runs: 1 });
    expect(typeof slaCall?.started_from).toBe("string");
    expect(readinessCall).toMatchObject({
      window_days: 7,
      health_window_days: 1,
      slo1_target_pct: 95
    });
  });
});
