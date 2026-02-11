import { emitTelemetry } from "./telemetry";

let isBootstrapped = false;

function recordNavigationTiming() {
  if (typeof performance === "undefined") {
    return;
  }
  const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
  if (!nav) {
    return;
  }
  emitTelemetry({
    category: "performance",
    name: "navigation_timing",
    severity: "info",
    attributes: {
      dom_content_loaded_ms: Math.round(nav.domContentLoadedEventEnd - nav.startTime),
      load_event_ms: Math.round(nav.loadEventEnd - nav.startTime),
      ttfb_ms: Math.round(nav.responseStart - nav.requestStart)
    }
  });
}

function observeWebVitals() {
  if (typeof PerformanceObserver === "undefined") {
    return;
  }

  try {
    const paintObserver = new PerformanceObserver((list) => {
      list.getEntries().forEach((entry) => {
        emitTelemetry({
          category: "web_vital",
          name: entry.name,
          severity: "info",
          attributes: { value: entry.startTime }
        });
      });
    });
    paintObserver.observe({ type: "paint", buffered: true });
  } catch {
    // Ignore unsupported browser API behavior.
  }

  try {
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1];
      if (!lastEntry) {
        return;
      }
      emitTelemetry({
        category: "web_vital",
        name: "largest-contentful-paint",
        severity: "info",
        attributes: { value: lastEntry.startTime }
      });
    });
    lcpObserver.observe({ type: "largest-contentful-paint", buffered: true });
  } catch {
    // Ignore unsupported browser API behavior.
  }

  try {
    let clsValue = 0;
    const clsObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const layoutShift = entry as PerformanceEntry & {
          value?: number;
          hadRecentInput?: boolean;
        };
        if (!layoutShift.hadRecentInput && typeof layoutShift.value === "number") {
          clsValue += layoutShift.value;
        }
      }
      emitTelemetry({
        category: "web_vital",
        name: "cumulative-layout-shift",
        severity: "info",
        attributes: { value: clsValue }
      });
    });
    clsObserver.observe({ type: "layout-shift", buffered: true });
  } catch {
    // Ignore unsupported browser API behavior.
  }
}

export function bootstrapFrontendObservability() {
  if (isBootstrapped || typeof window === "undefined") {
    return;
  }
  isBootstrapped = true;

  window.addEventListener("error", (event) => {
    emitTelemetry({
      category: "frontend_error",
      name: "window_error",
      severity: "error",
      attributes: {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno
      }
    });
  });

  window.addEventListener("unhandledrejection", (event) => {
    const reason =
      typeof event.reason === "string"
        ? event.reason
        : event.reason instanceof Error
          ? event.reason.message
          : JSON.stringify(event.reason);
    emitTelemetry({
      category: "frontend_error",
      name: "unhandled_rejection",
      severity: "error",
      attributes: { reason }
    });
  });

  recordNavigationTiming();
  observeWebVitals();
  emitTelemetry({
    category: "lifecycle",
    name: "frontend_bootstrap_complete",
    severity: "info"
  });
}
