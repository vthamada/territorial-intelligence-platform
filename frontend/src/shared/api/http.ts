import type { ApiErrorPayload } from "./types";

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
    return { message: error.message, requestId: error.requestId };
  }
  if (error instanceof Error) {
    return { message: error.message };
  }
  return { message: "Erro inesperado ao consultar API." };
}

type RequestOptions = {
  query?: Record<string, string | number | boolean | undefined>;
  timeoutMs?: number;
  retries?: number;
};

function shouldRetry(error: unknown): boolean {
  if (error instanceof ApiClientError) {
    return error.status >= 500;
  }
  return true;
}

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const retries = options.retries ?? DEFAULT_RETRIES;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const url = buildUrl(path, options.query);

  let attempt = 0;
  while (true) {
    const controller = new AbortController();
    const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, {
        method: "GET",
        headers: {
          Accept: "application/json"
        },
        signal: controller.signal
      });
      clearTimeout(timeoutHandle);
      if (!response.ok) {
        throw await decodeError(response);
      }
      return (await response.json()) as T;
    } catch (error) {
      clearTimeout(timeoutHandle);
      if (attempt >= retries || !shouldRetry(error)) {
        throw error;
      }
      attempt += 1;
      await new Promise((resolve) => setTimeout(resolve, 250 * attempt));
    }
  }
}
