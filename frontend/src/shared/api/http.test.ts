import { describe, expect, it, vi } from "vitest";

const { emitTelemetryMock } = vi.hoisted(() => ({
  emitTelemetryMock: vi.fn()
}));

vi.mock("../observability/telemetry", () => ({
  emitTelemetry: emitTelemetryMock
}));

import { ApiClientError, formatApiError, requestJson } from "./http";

describe("http client", () => {
  it("emits telemetry for successful requests", async () => {
    emitTelemetryMock.mockClear();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await requestJson<{ status: string }>("/health");

    expect(emitTelemetryMock).toHaveBeenCalledWith(
      expect.objectContaining({
        category: "api_request",
        name: "api_request_success",
        severity: "info",
        attributes: expect.objectContaining({
          method: "GET",
          path: "/health",
          status: 200,
          attempt: 1
        })
      })
    );
  });

  it("returns parsed JSON for successful requests", async () => {
    emitTelemetryMock.mockClear();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const payload = await requestJson<{ status: string }>("/health");
    expect(payload.status).toBe("ok");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("raises ApiClientError with request_id when backend returns error payload", async () => {
    emitTelemetryMock.mockClear();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "validation_error",
            message: "Invalid filter",
            request_id: "req-123"
          }
        }),
        {
          status: 422,
          headers: { "Content-Type": "application/json" }
        }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(requestJson("/ops/pipeline-runs")).rejects.toMatchObject({
      name: "ApiClientError",
      status: 422,
      requestId: "req-123"
    });
    expect(emitTelemetryMock).toHaveBeenCalledWith(
      expect.objectContaining({
        category: "api_request",
        name: "api_request_failed",
        severity: "error",
        attributes: expect.objectContaining({
          method: "GET",
          path: "/ops/pipeline-runs",
          status: 422,
          request_id: "req-123"
        })
      })
    );
  });

  it("retries once and then succeeds", async () => {
    emitTelemetryMock.mockClear();
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ total: 1 }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      );
    vi.stubGlobal("fetch", fetchMock);

    const payload = await requestJson<{ total: number }>("/ops/summary", { retries: 1 });
    expect(payload.total).toBe(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(emitTelemetryMock).toHaveBeenCalledWith(
      expect.objectContaining({
        category: "api_request",
        name: "api_request_retry",
        severity: "warn",
        attributes: expect.objectContaining({
          method: "GET",
          path: "/ops/summary",
          attempt: 1,
          max_attempts: 2
        })
      })
    );
    expect(emitTelemetryMock).toHaveBeenCalledWith(
      expect.objectContaining({
        category: "api_request",
        name: "api_request_success",
        severity: "info",
        attributes: expect.objectContaining({
          method: "GET",
          path: "/ops/summary",
          attempt: 2,
          status: 200
        })
      })
    );
  });

  it("supports POST with JSON body", async () => {
    emitTelemetryMock.mockClear();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const payload = await requestJson<{ ok: boolean }>("/scenarios/simulate", {
      method: "POST",
      body: { territory_id: "3121605", adjustment_percent: 10 }
    });

    expect(payload.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      method: "POST",
      headers: expect.objectContaining({ "Content-Type": "application/json" })
    });
  });
});

describe("formatApiError", () => {
  it("formats ApiClientError with request id", () => {
    const error = new ApiClientError("Boom", 500, "req-500", "internal_error");
    expect(formatApiError(error)).toEqual({ message: "Boom", requestId: "req-500" });
  });
});
