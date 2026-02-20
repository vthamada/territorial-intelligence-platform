import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RouteRuntimeErrorBoundary } from "./RouteRuntimeErrorBoundary";

const emitTelemetryMock = vi.fn();

vi.mock("../shared/observability/telemetry", () => ({
  emitTelemetry: (...args: unknown[]) => emitTelemetryMock(...args),
}));

function BrokenScreen(): JSX.Element {
  throw new Error("Erro intencional de render");
}

function ConditionalScreen({ shouldFail }: { shouldFail: boolean }) {
  if (shouldFail) {
    throw new Error("Erro condicional");
  }
  return <p>Tela recuperada</p>;
}

describe("RouteRuntimeErrorBoundary", () => {
  const originalConsoleError = console.error;

  afterEach(() => {
    emitTelemetryMock.mockReset();
    console.error = originalConsoleError;
  });

  it("shows error state and emits telemetry when child route crashes", () => {
    console.error = vi.fn();

    render(
      <RouteRuntimeErrorBoundary routeLabel="Insights">
        <BrokenScreen />
      </RouteRuntimeErrorBoundary>,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Falha na tela: Insights")).toBeInTheDocument();
    expect(screen.getByText("Erro intencional de render")).toBeInTheDocument();
    expect(emitTelemetryMock).toHaveBeenCalledWith(
      expect.objectContaining({
        category: "frontend_error",
        name: "route_runtime_error",
        severity: "error",
      }),
    );
  });

  it("recovers after retry when route stops failing", async () => {
    console.error = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <RouteRuntimeErrorBoundary routeLabel="Mapa">
        <ConditionalScreen shouldFail={true} />
      </RouteRuntimeErrorBoundary>,
    );

    expect(screen.getByText("Falha na tela: Mapa")).toBeInTheDocument();

    rerender(
      <RouteRuntimeErrorBoundary routeLabel="Mapa">
        <ConditionalScreen shouldFail={false} />
      </RouteRuntimeErrorBoundary>,
    );

    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(screen.getByText("Tela recuperada")).toBeInTheDocument();
  });
});
