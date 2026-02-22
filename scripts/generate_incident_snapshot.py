from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    src_str = str(SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

from app.ops_readiness import build_backend_readiness_report  # noqa: E402
from app.settings import get_settings  # noqa: E402


def _classify_incident(*, hard_failures: int, warnings: int, failed_runs: int, failed_checks: int) -> str:
    if hard_failures > 0 or failed_runs > 0 or failed_checks > 0:
        return "critical"
    if warnings > 0:
        return "high"
    return "normal"


def _recommended_actions(severity: str, *, hard_failures: int, failed_runs: int, failed_checks: int) -> list[str]:
    actions: list[str] = []
    if severity == "critical":
        actions.append("Bloquear novas cargas nao essenciais e priorizar estabilizacao operacional.")
    if hard_failures > 0:
        actions.append("Executar scripts/backend_readiness.py --strict e corrigir hard_failures primeiro.")
    if failed_runs > 0:
        actions.append("Reprocessar seletivamente jobs com falha via scripts/run_incremental_backfill.py.")
    if failed_checks > 0:
        actions.append("Inspecionar ops.pipeline_checks e ajustar threshold/dados de origem antes do proximo ciclo.")
    if severity == "high" and hard_failures == 0:
        actions.append("Agendar mitigacao para warnings recorrentes e acompanhar por 7 dias.")
    if not actions:
        actions.append("Manter rotina semanal e monitoramento padrao sem acao corretiva imediata.")
    return actions


def _fetch_recent_runs(conn: Any, *, lookback_days: int, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        sa.text(
            """
            SELECT
                run_id::text AS run_id,
                job_name,
                source,
                wave,
                reference_period,
                status,
                started_at_utc,
                finished_at_utc,
                errors_count,
                warnings_count
            FROM ops.pipeline_runs
            WHERE started_at_utc >= NOW() - make_interval(days => :lookback_days)
              AND status IN ('failed', 'blocked')
            ORDER BY started_at_utc DESC, run_id DESC
            LIMIT :limit
            """
        ),
        {"lookback_days": lookback_days, "limit": limit},
    ).mappings().all()
    return [dict(row) for row in rows]


def _fetch_recent_checks(conn: Any, *, lookback_days: int, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        sa.text(
            """
            SELECT
                pc.check_id,
                pc.run_id::text AS run_id,
                pr.job_name,
                pc.check_name,
                pc.status,
                pc.details,
                pc.created_at_utc
            FROM ops.pipeline_checks pc
            JOIN ops.pipeline_runs pr ON pr.run_id = pc.run_id
            WHERE pc.created_at_utc >= NOW() - make_interval(days => :lookback_days)
              AND pc.status = 'fail'
            ORDER BY pc.created_at_utc DESC, pc.check_id DESC
            LIMIT :limit
            """
        ),
        {"lookback_days": lookback_days, "limit": limit},
    ).mappings().all()
    return [dict(row) for row in rows]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an operational incident snapshot combining readiness, "
            "recent failed runs and failed checks."
        )
    )
    parser.add_argument("--window-days", type=int, default=7)
    parser.add_argument("--health-window-days", type=int, default=1)
    parser.add_argument("--slo1-target-pct", type=float, default=95.0)
    parser.add_argument("--include-blocked-as-success", action="store_true")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--max-items", type=int, default=50)
    parser.add_argument(
        "--output-json",
        default="data/reports/incident_snapshot.json",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    engine = sa.create_engine(settings.database_url)

    with engine.begin() as conn:
        readiness = build_backend_readiness_report(
            conn,
            window_days=max(1, int(args.window_days)),
            slo1_target_pct=float(args.slo1_target_pct),
            health_window_days=max(1, int(args.health_window_days)),
            include_blocked_as_success=bool(args.include_blocked_as_success),
        )
        recent_runs = _fetch_recent_runs(
            conn,
            lookback_days=max(1, int(args.lookback_days)),
            limit=max(1, int(args.max_items)),
        )
        recent_checks = _fetch_recent_checks(
            conn,
            lookback_days=max(1, int(args.lookback_days)),
            limit=max(1, int(args.max_items)),
        )

    severity = _classify_incident(
        hard_failures=len(readiness.get("hard_failures", [])),
        warnings=len(readiness.get("warnings", [])),
        failed_runs=len([row for row in recent_runs if row.get("status") == "failed"]),
        failed_checks=len(recent_checks),
    )

    payload = {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "severity": severity,
        "summary": {
            "hard_failures": len(readiness.get("hard_failures", [])),
            "warnings": len(readiness.get("warnings", [])),
            "failed_runs": len([row for row in recent_runs if row.get("status") == "failed"]),
            "blocked_runs": len([row for row in recent_runs if row.get("status") == "blocked"]),
            "failed_checks": len(recent_checks),
        },
        "recommended_actions": _recommended_actions(
            severity,
            hard_failures=len(readiness.get("hard_failures", [])),
            failed_runs=len([row for row in recent_runs if row.get("status") == "failed"]),
            failed_checks=len(recent_checks),
        ),
        "readiness": readiness,
        "recent_non_success_runs": recent_runs,
        "recent_failed_checks": recent_checks,
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print(
        "Incident snapshot:"
        f" severity={payload['severity']}"
        f" hard_failures={payload['summary']['hard_failures']}"
        f" warnings={payload['summary']['warnings']}"
        f" failed_runs={payload['summary']['failed_runs']}"
        f" failed_checks={payload['summary']['failed_checks']}"
    )
    print(f"Report written to {output_path.as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
