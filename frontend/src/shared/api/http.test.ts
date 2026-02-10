import { describe, expect, it, vi } from "vitest";
import { ApiClientError, formatApiError, requestJson } from "./http";

describe("http client", () => {
  it("returns parsed JSON for successful requests", async () => {
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
  });

  it("retries once and then succeeds", async () => {
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
  });
});

describe("formatApiError", () => {
  it("formats ApiClientError with request id", () => {
    const error = new ApiClientError("Boom", 500, "req-500", "internal_error");
    expect(formatApiError(error)).toEqual({ message: "Boom", requestId: "req-500" });
  });
});
