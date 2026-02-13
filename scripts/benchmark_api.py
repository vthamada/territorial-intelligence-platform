"""
Performance Benchmark — API executive endpoints (O8-03).

Measures p95 latency for critical GET/POST endpoints.
Usage:
    python scripts/benchmark_api.py [--base-url http://127.0.0.1:8000] [--rounds 30]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from urllib import request as urllib_request
from urllib.error import URLError

ENDPOINTS: list[dict] = [
    {"method": "GET", "path": "/v1/health", "label": "health"},
    {"method": "GET", "path": "/v1/kpis/overview?level=municipality&limit=8", "label": "kpis/overview"},
    {"method": "GET", "path": "/v1/priority/summary?level=municipality", "label": "priority/summary"},
    {"method": "GET", "path": "/v1/priority/list?level=municipality&limit=20", "label": "priority/list"},
    {"method": "GET", "path": "/v1/insights/highlights?level=municipality&limit=10", "label": "insights/highlights"},
    {"method": "GET", "path": "/v1/geo/choropleth?level=municipality&limit=100&metric=DATASUS_APS_COBERTURA&period=2025", "label": "geo/choropleth"},
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

TARGET_P95_MS = 800


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


def run_benchmark(base_url: str, rounds: int) -> list[dict]:
    """Run benchmark for all endpoints and return results."""
    results = []

    for ep in ENDPOINTS:
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
        success_rate = sum(1 for s in statuses if 200 <= s < 500) / len(statuses) * 100

        meets_target = p95 <= TARGET_P95_MS

        results.append({
            "endpoint": label,
            "method": ep["method"],
            "rounds": rounds,
            "avg_ms": round(avg, 1),
            "p50_ms": round(p50, 1),
            "p95_ms": round(p95, 1),
            "p99_ms": round(p99, 1),
            "min_ms": round(min(latencies), 1),
            "max_ms": round(max(latencies), 1),
            "success_rate_pct": round(success_rate, 1),
            "meets_p95_target": meets_target,
        })

    return results


def print_report(results: list[dict], target_ms: float) -> bool:
    """Print a formatted benchmark report. Returns True if all pass."""
    print(f"\n{'='*90}")
    print(f"  API Performance Benchmark Report  (target p95 <= {target_ms}ms)")
    print(f"{'='*90}")
    print(f"{'Endpoint':<25} {'Method':<6} {'Avg':>8} {'P50':>8} {'P95':>8} {'P99':>8} {'OK%':>6} {'Pass':>6}")
    print(f"{'-'*25} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*6} {'-'*6}")

    all_pass = True
    for r in results:
        mark = "OK" if r["meets_p95_target"] else "FAIL"
        if not r["meets_p95_target"]:
            all_pass = False
        print(
            f"{r['endpoint']:<25} {r['method']:<6} "
            f"{r['avg_ms']:>7.1f} {r['p50_ms']:>7.1f} {r['p95_ms']:>7.1f} {r['p99_ms']:>7.1f} "
            f"{r['success_rate_pct']:>5.1f} {mark:>6}"
        )

    print(f"{'='*90}")
    overall = "ALL PASS" if all_pass else "SOME ENDPOINTS EXCEED TARGET"
    print(f"  Result: {overall}")
    print(f"{'='*90}\n")

    return all_pass


def main() -> None:
    parser = argparse.ArgumentParser(description="API performance benchmark")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--rounds", type=int, default=30, help="Number of rounds per endpoint")
    parser.add_argument("--target-ms", type=float, default=TARGET_P95_MS, help="p95 target in ms")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    # Connectivity check
    try:
        urllib_request.urlopen(f"{args.base_url}/v1/health", timeout=5).read()
    except Exception:
        print(f"ERROR: Cannot reach API at {args.base_url}/v1/health", file=sys.stderr)
        print("Make sure the server is running.", file=sys.stderr)
        sys.exit(1)

    results = run_benchmark(args.base_url, args.rounds)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        all_pass = print_report(results, args.target_ms)
        if not all_pass:
            sys.exit(1)


if __name__ == "__main__":
    main()
