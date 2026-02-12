import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OpsChecksPage } from "./OpsChecksPage";
import { OpsConnectorsPage } from "./OpsConnectorsPage";
import { OpsFrontendEventsPage } from "./OpsFrontendEventsPage";
import { OpsRunsPage } from "./OpsRunsPage";
import { OpsSourceCoveragePage } from "./OpsSourceCoveragePage";
import {
  getConnectorRegistry,
  getFrontendEvents,
  getOpsSourceCoverage,
  getPipelineChecks,
  getPipelineRuns
} from "../../../shared/api/ops";

vi.mock("../../../shared/api/ops", () => ({
  getPipelineRuns: vi.fn(),
  getPipelineChecks: vi.fn(),
  getConnectorRegistry: vi.fn(),
  getFrontendEvents: vi.fn(),
  getOpsSourceCoverage: vi.fn()
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
});
