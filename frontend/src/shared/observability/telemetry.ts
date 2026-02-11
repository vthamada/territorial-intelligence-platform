export type TelemetrySeverity = "info" | "warn" | "error";

export type TelemetryEvent = {
  category: "frontend_error" | "web_vital" | "performance" | "lifecycle" | "api_request";
  name: string;
  severity: TelemetrySeverity;
  attributes?: Record<string, unknown>;
  timestamp_utc: string;
};

type TelemetryEmitterOptions = {
  endpointUrl?: string;
  transport?: (event: TelemetryEvent) => void;
};

function defaultTransport(endpointUrl: string | undefined, event: TelemetryEvent) {
  if (!endpointUrl) {
    return;
  }

  const payload = JSON.stringify(event);
  const canUseBeacon = typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function";
  if (canUseBeacon) {
    try {
      const sent = navigator.sendBeacon(
        endpointUrl,
        new Blob([payload], { type: "application/json" })
      );
      if (sent) {
        return;
      }
    } catch {
      // Fall back to fetch below.
    }
  }

  void fetch(endpointUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload,
    keepalive: true
  }).catch(() => {
    // Telemetry must not break UX.
  });
}

export function createTelemetryEmitter(options?: TelemetryEmitterOptions) {
  const endpointUrl = options?.endpointUrl;
  const transport = options?.transport;

  return (event: Omit<TelemetryEvent, "timestamp_utc">) => {
    const normalized: TelemetryEvent = {
      ...event,
      timestamp_utc: new Date().toISOString()
    };

    if (import.meta.env.DEV && normalized.severity !== "info") {
      // Helpful local diagnostics while keeping production output quiet.
      // eslint-disable-next-line no-console
      console.warn("[frontend-telemetry]", normalized);
    }

    if (transport) {
      transport(normalized);
      return;
    }
    defaultTransport(endpointUrl, normalized);
  };
}

export const emitTelemetry = createTelemetryEmitter({
  endpointUrl: import.meta.env.VITE_FRONTEND_OBSERVABILITY_URL as string | undefined
});
