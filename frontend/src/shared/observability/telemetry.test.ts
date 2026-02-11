import { describe, expect, it, vi } from "vitest";
import { createTelemetryEmitter } from "./telemetry";

describe("telemetry emitter", () => {
  it("normalizes event with timestamp and delegates to transport", () => {
    const transport = vi.fn();
    const emit = createTelemetryEmitter({ transport });

    emit({
      category: "lifecycle",
      name: "frontend_bootstrap_complete",
      severity: "info",
      attributes: { sample: true }
    });

    expect(transport).toHaveBeenCalledTimes(1);
    const payload = transport.mock.calls[0][0];
    expect(payload.category).toBe("lifecycle");
    expect(payload.name).toBe("frontend_bootstrap_complete");
    expect(payload.severity).toBe("info");
    expect(typeof payload.timestamp_utc).toBe("string");
  });
});
