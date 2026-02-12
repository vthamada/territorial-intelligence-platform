import type { ApiErrorPayload } from "./types";
import { emitTelemetry } from "../observability/telemetry";

const DEFAULT_TIMEOUT_MS = 15_000;
const DEFAULT_RETRIES = 1;
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/v1";

export class ApiClientError extends Error {
  status: number;
  requestId?: string;
  code?: string;

  constructor(message: string, status: number, requestId?: string, code?: string) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.requestId = requestId;
    this.code = code;
  }
}

function buildUrl(path: string, query?: Record<string, string | number | boolean | undefined>) {
  const url = new URL(path.replace(/^\//, ""), `${API_BASE_URL.replace(/\/$/, "")}/`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === "") {
        continue;
      }
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function decodeError(response: Response): Promise<ApiClientError> {
  let payload: ApiErrorPayload | null = null;
  try {
    const raw = await response.text();
    payload = raw ? (JSON.parse(raw) as ApiErrorPayload) : null;
  } catch {
    payload = null;
  }

  const requestId =
    payload?.error?.request_id ??
    (payload as { error?: { requestId?: string } } | null)?.error?.requestId ??
    response.headers.get("x-request-id") ??
    undefined;
  const message = payload?.error?.message ?? `Request failed with status ${response.status}`;
  const code = payload?.error?.code;
  return new ApiClientError(message, response.status, requestId, code);
}

export function formatApiError(error: unknown): { message: string; requestId?: string } {
  if (error instanceof ApiClientError) {
    if (error.message === "Request failed.") {
      return {
        message: `Falha na API (status ${error.status}). Consulte os logs do backend para mais detalhes.`,
        requestId: error.requestId
      };
    }
    return { message: error.message, requestId: error.requestId };
  }
  if (error instanceof Error) {
    if (error.message === "Failed to fetch") {
      return { message: "Nao foi possivel conectar com a API. Verifique se o backend esta ativo." };
    }
    return { message: error.message };
  }
  return { message: "Erro inesperado ao consultar API." };
}

type RequestOptions = {
  query?: Record<string, string | number | boolean | undefined>;
  timeoutMs?: number;
  retries?: number;
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
};

function shouldRetry(error: unknown): boolean {
  if (error instanceof ApiClientError) {
    return error.status >= 500;
  }
  return true;
}

function nowMs(): number {
  if (typeof performance !== "undefined" && typeof performance.now === "function") {
    return performance.now();
  }
  return Date.now();
}

function isAbortError(error: unknown): boolean {
  if (typeof DOMException === "undefined") {
    return false;
  }
  return error instanceof DOMException && error.name === "AbortError";
}

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const retries = options.retries ?? DEFAULT_RETRIES;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const url = buildUrl(path, options.query);
  const method = options.method ?? "GET";
  const retriesAllowed = method === "GET" ? retries : 0;

  let attempt = 0;
  while (true) {
    const attemptStart = nowMs();
    const controller = new AbortController();
    const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const headers: Record<string, string> = {
        Accept: "application/json",
        ...(options.headers ?? {}),
      };

      let body: string | undefined;
      if (options.body !== undefined) {
        body = JSON.stringify(options.body);
        headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
      }

      const response = await fetch(url, {
        method,
        headers,
        body,
        signal: controller.signal
      });
      clearTimeout(timeoutHandle);
      if (!response.ok) {
        throw await decodeError(response);
      }

      const payload = (await response.json()) as T;
      emitTelemetry({
        category: "api_request",
        name: "api_request_success",
        severity: "info",
        attributes: {
          method,
          path,
          status: response.status,
          duration_ms: Math.round(nowMs() - attemptStart),
          attempt: attempt + 1
        }
      });
      return payload;
    } catch (error) {
      clearTimeout(timeoutHandle);
      const willRetry = attempt < retriesAllowed && shouldRetry(error);
      const durationMs = Math.round(nowMs() - attemptStart);

      if (willRetry) {
        emitTelemetry({
          category: "api_request",
          name: "api_request_retry",
          severity: "warn",
          attributes: {
            method,
            path,
            attempt: attempt + 1,
            max_attempts: retriesAllowed + 1,
            duration_ms: durationMs,
            status: error instanceof ApiClientError ? error.status : undefined,
            code: error instanceof ApiClientError ? error.code : undefined,
            request_id: error instanceof ApiClientError ? error.requestId : undefined
          }
        });
      } else {
        emitTelemetry({
          category: "api_request",
          name: "api_request_failed",
          severity: "error",
          attributes: {
            method,
            path,
            attempt: attempt + 1,
            max_attempts: retriesAllowed + 1,
            duration_ms: durationMs,
            status: error instanceof ApiClientError ? error.status : undefined,
            code: error instanceof ApiClientError ? error.code : undefined,
            request_id: error instanceof ApiClientError ? error.requestId : undefined,
            is_timeout: isAbortError(error),
            message: error instanceof Error ? error.message : "unknown_error"
          }
        });
      }

      if (!willRetry) {
        throw error;
      }
      attempt += 1;
      await new Promise((resolve) => setTimeout(resolve, 250 * attempt));
    }
  }
}
