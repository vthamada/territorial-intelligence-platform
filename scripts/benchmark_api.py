"""
Performance benchmark for API endpoint suites.

Measures p95 latency for critical endpoints with suite-specific targets.
Usage:
    python scripts/benchmark_api.py --suite executive [--base-url http://127.0.0.1:8000] [--rounds 30]
    python scripts/benchmark_api.py --suite urban [--base-url http://127.0.0.1:8000] [--rounds 30]
    python scripts/benchmark_api.py --suite ops [--base-url http://127.0.0.1:8000] [--rounds 30]
    python scripts/benchmark_api.py --suite all [--base-url http://127.0.0.1:8000] [--rounds 30]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from urllib import request as urllib_request
from urllib.error import URLError

EXECUTIVE_ENDPOINTS: list[dict] = [
    {"method": "GET", "path": "/v1/health", "label": "health"},
    {"method": "GET", "path": "/v1/kpis/overview?level=municipality&limit=8", "label": "kpis/overview"},
    {"method": "GET", "path": "/v1/priority/summary?level=municipality", "label": "priority/summary"},
    {"method": "GET", "path": "/v1/priority/list?level=municipality&limit=20", "label": "priority/list"},
    {"method": "GET", "path": "/v1/insights/highlights?level=municipality&limit=10", "label": "insights/highlights"},
    {
        "method": "GET",
        "path": "/v1/geo/choropleth?level=municipality&limit=100&metric=DATASUS_APS_COBERTURA&period=2025",
        "label": "geo/choropleth",
    },
    {"method": "GET", "path": "/v1/map/layers", "label": "map/layers"},
    {"method": "GET", "path": "/v1/map/style-metadata", "label": "map/style-metadata"},
    {"method": "GET", "path": "/v1/electorate/summary?level=municipality", "label": "electorate/summary"},
    {"method": "GET", "path": "/v1/electorate/map?level=municipality&limit=100", "label": "electorate/map"},
    {
        "method": "POST",
        "path": "/v1/scenarios/simulate",
        "label": "scenarios/simulate",
        "body": {
            "territory_id": "3121605",
            "period": "2025",
            "level": "municipality",
            "domain": "saude",
            "adjustment_percent": 10,
            "limit": 50,
        },
    },
    {
        "method": "POST",
        "path": "/v1/briefs",
        "label": "briefs",
        "body": {
            "territory_id": "3121605",
            "period": "2025",
            "level": "municipality",
            "limit": 20,
        },
    },
]

URBAN_ENDPOINTS: list[dict] = [
    {
        "method": "GET",
        "path": "/v1/map/urban/roads?bbox=-43.70,-18.30,-43.50,-18.10&limit=500",
        "label": "map/urban/roads",
    },
    {
        "method": "GET",
        "path": "/v1/map/urban/pois?bbox=-43.70,-18.30,-43.50,-18.10&limit=500",
        "label": "map/urban/pois",
    },
    {
        "method": "GET",
        "path": "/v1/map/urban/nearby-pois?lon=-43.601&lat=-18.244&radius_m=1500&limit=200",
        "label": "map/urban/nearby-pois",
    },
    {
        "method": "GET",
        "path": "/v1/map/urban/geocode?q=Rua&kind=all&limit=50",
        "label": "map/urban/geocode",
    },
]

OPS_ENDPOINTS: list[dict] = [
    {"method": "GET", "path": "/v1/ops/summary", "label": "ops/summary"},
    {"method": "GET", "path": "/v1/ops/readiness", "label": "ops/readiness"},
    {
        "method": "GET",
        "path": "/v1/ops/pipeline-runs?page=1&page_size=50",
        "label": "ops/pipeline-runs",
    },
    {
        "method": "GET",
        "path": "/v1/ops/pipeline-checks?page=1&page_size=50",
        "label": "ops/pipeline-checks",
    },
    {
        "method": "GET",
        "path": "/v1/ops/connector-registry?page=1&page_size=50",
        "label": "ops/connector-registry",
    },
    {"method": "GET", "path": "/v1/ops/source-coverage", "label": "ops/source-coverage"},
    {"method": "GET", "path": "/v1/ops/sla", "label": "ops/sla"},
    {
        "method": "GET",
        "path": "/v1/ops/timeseries?entity=runs&granularity=day",
        "label": "ops/timeseries",
    },
]

SUITE_ENDPOINTS: dict[str, list[dict]] = {
    "executive": EXECUTIVE_ENDPOINTS,
    "urban": URBAN_ENDPOINTS,
    "ops": OPS_ENDPOINTS,
    "all": EXECUTIVE_ENDPOINTS + URBAN_ENDPOINTS + OPS_ENDPOINTS,
}

DEFAULT_TARGET_P95_MS: dict[str, float] = {
    "executive": 800.0,
    "urban": 1000.0,
    "ops": 1500.0,
    "all": 1000.0,
}


def _percentile(data: list[float], pct: float) -> float:
    """Calculate the percentile value from a sorted list."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * pct / 100.0
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[f]
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


def _do_request(base_url: str, endpoint: dict) -> tuple[float, int]:
    """Execute a single request and return (latency_ms, status_code)."""
    url = f"{base_url}{endpoint['path']}"
    body_bytes = None
    headers = {"Accept": "application/json"}

    if endpoint["method"] == "POST":
        body_bytes = json.dumps(endpoint.get("body", {})).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib_request.Request(url, data=body_bytes, headers=headers, method=endpoint["method"])

    start = time.perf_counter()
    try:
        with urllib_request.urlopen(req, timeout=30) as resp:
            resp.read()
            elapsed_ms = (time.perf_counter() - start) * 1000
            return elapsed_ms, resp.status
    except URLError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        status = getattr(exc, "code", 0) if hasattr(exc, "code") else 0
        return elapsed_ms, status


def run_benchmark(base_url: str, rounds: int, endpoints: list[dict], target_ms: float) -> list[dict]:
    """Run benchmark for selected endpoints and return results."""
    results = []

    for ep in endpoints:
        label = ep["label"]
        latencies: list[float] = []
        statuses: list[int] = []

        # Warm-up round (not counted)
        _do_request(base_url, ep)

        for _ in range(rounds):
            lat, status = _do_request(base_url, ep)
            latencies.append(lat)
            statuses.append(status)

        p50 = _percentile(latencies, 50)
        p95 = _percentile(latencies, 95)
        p99 = _percentile(latencies, 99)
        avg = statistics.mean(latencies)
        success_rate = sum(1 for s in statuses if 200 <= s < 300) / len(statuses) * 100

        results.append(
            {
                "endpoint": label,
                "method": ep["method"],
                "rounds": rounds,
                "target_p95_ms": round(target_ms, 1),
                "avg_ms": round(avg, 1),
                "p50_ms": round(p50, 1),
                "p95_ms": round(p95, 1),
                "p99_ms": round(p99, 1),
                "min_ms": round(min(latencies), 1),
                "max_ms": round(max(latencies), 1),
                "success_rate_pct": round(success_rate, 1),
                "meets_p95_target": p95 <= target_ms,
                "meets_http_target": success_rate == 100.0,
                "pass": bool(p95 <= target_ms and success_rate == 100.0),
            }
        )

    return results


def print_report(results: list[dict], target_ms: float, suite: str) -> bool:
    """Print a formatted benchmark report. Returns True if all pass."""
    print(f"\n{'='*102}")
    print(f"  API Performance Benchmark Report ({suite})  (target p95 <= {target_ms}ms)")
    print(f"{'='*102}")
    print(
        f"{'Endpoint':<28} {'Method':<6} {'Avg':>8} {'P50':>8} {'P95':>8} {'P99':>8} "
        f"{'OK%':>6} {'Target':>8} {'Pass':>6}"
    )
    print(f"{'-'*28} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*6} {'-'*8} {'-'*6}")

    all_pass = True
    for r in results:
        mark = "OK" if r["pass"] else "FAIL"
        if not r["pass"]:
            all_pass = False
        print(
            f"{r['endpoint']:<28} {r['method']:<6} "
            f"{r['avg_ms']:>7.1f} {r['p50_ms']:>7.1f} {r['p95_ms']:>7.1f} {r['p99_ms']:>7.1f} "
            f"{r['success_rate_pct']:>5.1f} {r['target_p95_ms']:>7.1f} {mark:>6}"
        )

    print(f"{'='*102}")
    overall = "ALL PASS" if all_pass else "SOME ENDPOINTS EXCEED TARGET"
    print(f"  Result: {overall}")
    print(f"{'='*102}\n")

    return all_pass


def main() -> None:
    parser = argparse.ArgumentParser(description="API performance benchmark")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--rounds", type=int, default=30, help="Number of rounds per endpoint")
    parser.add_argument(
        "--suite",
        choices=["executive", "urban", "ops", "all"],
        default="executive",
        help="Benchmark suite to execute",
    )
    parser.add_argument(
        "--target-ms",
        type=float,
        default=None,
        help="Override p95 target in ms (defaults per suite)",
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--json-output",
        default=None,
        help="Optional path to persist JSON results (useful for issue evidence)",
    )
    args = parser.parse_args()

    target_ms = float(args.target_ms) if args.target_ms is not None else DEFAULT_TARGET_P95_MS[args.suite]
    endpoints = SUITE_ENDPOINTS[args.suite]

    # Connectivity check
    try:
        urllib_request.urlopen(f"{args.base_url}/v1/health", timeout=5).read()
    except Exception:
        print(f"ERROR: Cannot reach API at {args.base_url}/v1/health", file=sys.stderr)
        print("Make sure the server is running.", file=sys.stderr)
        sys.exit(1)

    results = run_benchmark(args.base_url, args.rounds, endpoints=endpoints, target_ms=target_ms)
    output_payload = {
        "suite": args.suite,
        "target_p95_ms": target_ms,
        "rounds": args.rounds,
        "base_url": args.base_url,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": results,
    }

    if args.json:
        print(json.dumps(output_payload, indent=2))
    else:
        all_pass = print_report(results, target_ms=target_ms, suite=args.suite)
        if not all_pass:
            sys.exit(1)

    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as fp:
            json.dump(output_payload, fp, indent=2)


if __name__ == "__main__":
    main()
