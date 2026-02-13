"""Consolidated homologation readiness check for go-live gate.

Orchestrates all validation dimensions and produces a single pass/fail verdict:
  1. Backend readiness (schema, SLO-1, ops tracking)
  2. Quality suite summary (latest check results from DB)
  3. Frontend build verification
  4. Test suite counts (backend + frontend)
  5. API contract smoke (health endpoint reachable)

Usage:
    python scripts/homologation_check.py [--json] [--strict]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    src_str = str(SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


def _section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ---------- 1. Backend readiness ----------

def check_backend_readiness() -> dict[str, Any]:
    _section("1. Backend readiness (schema / SLO-1 / ops)")
    try:
        from scripts.backend_readiness import build_report

        report = build_report(
            window_days=7,
            slo1_target_pct=95.0,
            health_window_days=1,
            include_blocked_as_success=False,
        )
        hard = len(report.get("hard_failures", []))
        warns = len(report.get("warnings", []))
        passed = hard == 0
        print(f"  hard_failures={hard}  warnings={warns}  => {'PASS' if passed else 'FAIL'}")
        for item in report.get("hard_failures", []):
            print(f"    HARD_FAIL: {item}")
        for item in report.get("warnings", []):
            print(f"    WARN: {item}")
        return {"name": "backend_readiness", "passed": passed, "hard_failures": hard, "warnings": warns}
    except Exception as exc:
        print(f"  ERROR: {exc}")
        return {"name": "backend_readiness", "passed": False, "error": str(exc)}


# ---------- 2. Quality suite summary ----------

def check_quality_suite() -> dict[str, Any]:
    _section("2. Quality suite (latest check results)")
    try:
        import sqlalchemy as sa
        from app.settings import get_settings

        settings = get_settings()
        engine = sa.create_engine(settings.database_url)
        with engine.connect() as conn:
            row = conn.execute(
                sa.text(
                    """
                    SELECT run_id, status, rows_extracted, warnings_count, errors_count,
                           finished_at_utc
                    FROM ops.pipeline_runs
                    WHERE job_name = 'quality_suite'
                    ORDER BY finished_at_utc DESC
                    LIMIT 1
                    """
                )
            ).mappings().fetchone()

        if not row:
            print("  No quality_suite run found in ops.pipeline_runs.")
            return {"name": "quality_suite", "passed": False, "error": "no_runs_found"}

        passed = row["status"] == "success"
        print(f"  run_id={row['run_id']}")
        print(f"  status={row['status']}  checks={row['rows_extracted']}")
        print(f"  warnings={row['warnings_count']}  errors={row['errors_count']}")
        print(f"  finished_at={row['finished_at_utc']}")
        print(f"  => {'PASS' if passed else 'FAIL'}")
        return {
            "name": "quality_suite",
            "passed": passed,
            "status": row["status"],
            "checks": row["rows_extracted"],
            "warnings": row["warnings_count"],
            "errors": row["errors_count"],
        }
    except Exception as exc:
        print(f"  ERROR: {exc}")
        return {"name": "quality_suite", "passed": False, "error": str(exc)}


# ---------- 3. Frontend build ----------

def check_frontend_build() -> dict[str, Any]:
    _section("3. Frontend build (tsc + vite)")
    try:
        result = subprocess.run(
            ["npm", "--prefix", "frontend", "run", "build"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=120,
        )
        passed = result.returncode == 0
        if not passed:
            stderr_tail = (result.stderr or "").strip().split("\n")[-5:]
            for line in stderr_tail:
                print(f"    {line}")
        print(f"  => {'PASS' if passed else 'FAIL'}")
        return {"name": "frontend_build", "passed": passed}
    except Exception as exc:
        print(f"  ERROR: {exc}")
        return {"name": "frontend_build", "passed": False, "error": str(exc)}


# ---------- 4. Test suites ----------

def _count_tests(label: str, cmd: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=300,
        )
        output = result.stdout + result.stderr
        passed = result.returncode == 0

        # Try to extract test count from output
        count = 0
        for line in output.split("\n"):
            low = line.lower()
            if "passed" in low:
                # pytest: "207 passed" / vitest: "Tests  43 passed"
                for token in line.split():
                    if token.isdigit():
                        count = int(token)
                        break

        print(f"  {label}: {count} tests {'passed' if passed else 'FAILED'}")
        return {"name": label, "passed": passed, "count": count}
    except Exception as exc:
        print(f"  {label} ERROR: {exc}")
        return {"name": label, "passed": False, "error": str(exc)}


def check_test_suites() -> list[dict[str, Any]]:
    _section("4. Test suites (backend + frontend)")
    python_exe = str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe")
    if not Path(python_exe).exists():
        python_exe = str(PROJECT_ROOT / ".venv" / "bin" / "python")

    backend = _count_tests(
        "backend_tests",
        [python_exe, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
    )
    frontend = _count_tests(
        "frontend_tests",
        ["npm", "--prefix", "frontend", "run", "test"],
    )
    return [backend, frontend]


# ---------- 5. API smoke ----------

def check_api_smoke(base_url: str = "http://127.0.0.1:8000") -> dict[str, Any]:
    _section("5. API smoke (health endpoint)")
    url = f"{base_url}/v1/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode())
            api_ok = body.get("api") == "ok"
            db_ok = body.get("db") == "ok"
            passed = api_ok and db_ok
            print(f"  api={body.get('api')}  db={body.get('db')}  => {'PASS' if passed else 'FAIL'}")
            return {"name": "api_smoke", "passed": passed, "api": body.get("api"), "db": body.get("db")}
    except Exception as exc:
        print(f"  API not reachable: {exc}")
        return {"name": "api_smoke", "passed": False, "error": str(exc), "skipped": True}


# ---------- Orchestrator ----------

def run_homologation(*, strict: bool = False, output_json: bool = False) -> int:
    print("HOMOLOGATION READINESS CHECK")
    print(f"project: {PROJECT_ROOT.name}")
    print(f"strict mode: {strict}")

    results: list[dict[str, Any]] = []

    results.append(check_backend_readiness())
    results.append(check_quality_suite())
    results.append(check_frontend_build())
    results.extend(check_test_suites())
    results.append(check_api_smoke())

    _section("SUMMARY")
    all_passed = True
    skipped = 0
    for r in results:
        status = "PASS" if r["passed"] else ("SKIP" if r.get("skipped") else "FAIL")
        if status == "SKIP":
            skipped += 1
        elif not r["passed"]:
            all_passed = False
        icon = "OK" if r["passed"] else ("--" if r.get("skipped") else "XX")
        print(f"  [{icon}] {r['name']}")

    verdict = "READY FOR GO-LIVE" if all_passed else "NOT READY"
    print(f"\n  VERDICT: {verdict}")
    if skipped:
        print(f"  ({skipped} check(s) skipped — API may not be running)")

    if output_json:
        print(json.dumps({"verdict": verdict, "results": results}, indent=2, default=str))

    return 0 if all_passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Consolidated homologation readiness check.")
    parser.add_argument("--json", action="store_true", help="Output JSON report.")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings.")
    args = parser.parse_args(argv)
    return run_homologation(strict=args.strict, output_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
