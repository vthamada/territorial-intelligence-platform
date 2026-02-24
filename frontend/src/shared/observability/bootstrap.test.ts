import { beforeEach, describe, expect, it, vi } from "vitest";
import { emitTelemetry } from "./telemetry";
import { bootstrapFrontendObservability } from "./bootstrap";

vi.mock("./telemetry", () => ({
  emitTelemetry: vi.fn(),
}));

describe("bootstrapFrontendObservability", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("wires global error handlers and emits bootstrap lifecycle once", () => {
    bootstrapFrontendObservability();
    bootstrapFrontendObservability();

    window.dispatchEvent(
      new ErrorEvent("error", {
        message: "Erro global de teste",
        filename: "app.tsx",
        lineno: 12,
        colno: 4,
      }),
    );

    const rejectionEvent = new Event("unhandledrejection") as PromiseRejectionEvent;
    Object.defineProperty(rejectionEvent, "reason", {
      value: "Falha async",
      configurable: true,
    });
    window.dispatchEvent(rejectionEvent);

    const payloads = vi.mocked(emitTelemetry).mock.calls.map(([event]) => event);
    const eventNames = payloads.map((payload) => payload.name);

    expect(eventNames.filter((name) => name === "frontend_bootstrap_complete")).toHaveLength(1);
    expect(eventNames).toContain("window_error");
    expect(eventNames).toContain("unhandled_rejection");
  });
});
