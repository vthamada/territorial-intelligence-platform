from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import text

from app.ops_readiness import build_backend_readiness_report


class SqlExecutor(Protocol):
    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Any: ...


def _scorecard_status_counts(executor: SqlExecutor) -> dict[str, int]:
    rows = executor.execute(
        text(
            """
            SELECT status::text AS status, COUNT(*)::bigint AS count
            FROM ops.v_data_coverage_scorecard
            GROUP BY status::text
            ORDER BY status::text
            """
        )
    ).fetchall()
    return {str(row[0]): int(row[1]) for row in rows}


def _incident_window_summary(executor: SqlExecutor, *, window_days: int) -> dict[str, Any]:
    run_rows = executor.execute(
        text(
            """
            SELECT status::text AS status, COUNT(*)::bigint AS count
            FROM ops.pipeline_runs
            WHERE started_at_utc >= NOW() - make_interval(days => :window_days)
            GROUP BY status::text
            ORDER BY status::text
            """
        ),
        {"window_days": window_days},
    ).fetchall()
    runs_by_status = {str(row[0]): int(row[1]) for row in run_rows}

    failed_checks = executor.execute(
        text(
            """
            SELECT COUNT(*)::bigint
            FROM ops.pipeline_checks
            WHERE created_at_utc >= NOW() - make_interval(days => :window_days)
              AND status = 'fail'
            """
        ),
        {"window_days": window_days},
    ).scalar_one()

    return {
        "window_days": window_days,
        "runs_total": int(sum(runs_by_status.values())),
        "runs_by_status": runs_by_status,
        "failed_runs": int(runs_by_status.get("failed", 0)),
        "blocked_runs": int(runs_by_status.get("blocked", 0)),
        "failed_checks": int(failed_checks or 0),
    }


def _unresolved_failed_checks_summary(executor: SqlExecutor, *, window_days: int) -> dict[str, Any]:
    rows = executor.execute(
        text(
            """
            WITH checks AS (
                SELECT
                    pr.job_name,
                    pc.check_name,
                    pc.status,
                    pc.created_at_utc
                FROM ops.pipeline_checks pc
                JOIN ops.pipeline_runs pr ON pr.run_id = pc.run_id
                WHERE pc.created_at_utc >= NOW() - make_interval(days => :window_days)
            ),
            runs AS (
                SELECT
                    pr.job_name,
                    pr.status,
                    pr.started_at_utc
                FROM ops.pipeline_runs pr
                WHERE pr.started_at_utc >= NOW() - make_interval(days => :window_days)
            ),
            unresolved AS (
                SELECT
                    f.job_name,
                    f.check_name
                FROM checks f
                WHERE f.status = 'fail'
                  AND NOT EXISTS (
                        SELECT 1
                        FROM checks p
                        WHERE p.job_name = f.job_name
                          AND p.check_name = f.check_name
                          AND p.status = 'pass'
                          AND p.created_at_utc > f.created_at_utc
                  )
                  AND NOT EXISTS (
                        SELECT 1
                        FROM runs r
                        WHERE r.job_name = f.job_name
                          AND r.status = 'success'
                          AND r.started_at_utc > f.created_at_utc
                  )
            )
            SELECT
                job_name,
                check_name,
                COUNT(*)::bigint AS count
            FROM unresolved
            GROUP BY job_name, check_name
            ORDER BY count DESC, job_name, check_name
            """
        ),
        {"window_days": window_days},
    ).fetchall()
    items = [
        {
            "job_name": str(row[0]),
            "check_name": str(row[1]),
            "count": int(row[2]),
        }
        for row in rows
    ]
    return {
        "window_days": window_days,
        "total": int(sum(item["count"] for item in items)),
        "items": items,
    }


def _unresolved_failed_runs_summary(executor: SqlExecutor, *, window_days: int) -> dict[str, Any]:
    rows = executor.execute(
        text(
            """
            WITH runs AS (
                SELECT
                    job_name,
                    status,
                    started_at_utc
                FROM ops.pipeline_runs
                WHERE started_at_utc >= NOW() - make_interval(days => :window_days)
            ),
            unresolved AS (
                SELECT
                    f.job_name
                FROM runs f
                WHERE f.status = 'failed'
                  AND NOT EXISTS (
                        SELECT 1
                        FROM runs s
                        WHERE s.job_name = f.job_name
                          AND s.status = 'success'
                          AND s.started_at_utc > f.started_at_utc
                  )
            )
            SELECT
                job_name,
                COUNT(*)::bigint AS count
            FROM unresolved
            GROUP BY job_name
            ORDER BY count DESC, job_name
            """
        ),
        {"window_days": window_days},
    ).fetchall()
    items = [
        {
            "job_name": str(row[0]),
            "count": int(row[1]),
        }
        for row in rows
    ]
    return {
        "window_days": window_days,
        "total": int(sum(item["count"] for item in items)),
        "items": items,
    }


def _classify_severity(*, hard_failures: int, warnings: int, failed_runs: int, failed_checks: int) -> str:
    if hard_failures > 0 or failed_runs > 0 or failed_checks > 0:
        return "critical"
    if warnings > 0:
        return "high"
    return "normal"


def _recommended_actions(
    *,
    strict: bool,
    hard_failures: int,
    warnings: int,
    failed_runs: int,
    failed_checks: int,
    scorecard_fail_metrics: int,
) -> list[str]:
    actions: list[str] = []
    if hard_failures > 0:
        actions.append("Corrigir hard failures de readiness antes de novas cargas nao essenciais.")
    if failed_runs > 0:
        actions.append("Executar reprocessamento seletivo para jobs com status failed.")
    if failed_checks > 0:
        actions.append("Corrigir checks com status fail antes do proximo ciclo operacional.")
    if scorecard_fail_metrics > 0:
        actions.append("Tratar metricas com status fail no scorecard de cobertura de dados.")
    if strict and warnings > 0 and hard_failures == 0:
        actions.append("Mitigar warnings para atingir criterio strict sem pendencias operacionais.")
    if not actions:
        actions.append("Manter monitoramento padrao e registrar consolidacao semanal.")
    return actions


def build_ops_robustness_window_report(
    executor: SqlExecutor,
    *,
    window_days: int,
    health_window_days: int,
    slo1_target_pct: float,
    include_blocked_as_success: bool,
    strict: bool,
) -> dict[str, Any]:
    readiness = build_backend_readiness_report(
        executor,
        window_days=window_days,
        slo1_target_pct=slo1_target_pct,
        health_window_days=health_window_days,
        include_blocked_as_success=include_blocked_as_success,
    )
    scorecard_status_counts = _scorecard_status_counts(executor)
    incident_window = _incident_window_summary(executor, window_days=window_days)
    unresolved_failed_checks = _unresolved_failed_checks_summary(executor, window_days=window_days)
    unresolved_failed_runs = _unresolved_failed_runs_summary(executor, window_days=window_days)

    hard_failures = int(len(readiness.get("hard_failures", [])))
    warnings = int(len(readiness.get("warnings", [])))
    scorecard_fail_metrics = int(scorecard_status_counts.get("fail", 0))
    slo1_current = readiness.get("slo1_current", {})

    gates = {
        "slo_1_window_target": {
            "pass": bool(readiness.get("slo1", {}).get("meets_target")),
            "value": readiness.get("slo1", {}).get("success_rate_pct"),
            "target": slo1_target_pct,
        },
        "slo_1_health_window_target": {
            "pass": bool(slo1_current.get("meets_target")),
            "value": slo1_current.get("success_rate_pct"),
            "target": slo1_target_pct,
            "window_days": slo1_current.get("window_days"),
        },
        "readiness_no_hard_failures": {
            "pass": hard_failures == 0,
            "value": hard_failures,
            "target": 0,
        },
        "quality_no_unresolved_failed_checks_window": {
            "pass": unresolved_failed_checks["total"] == 0,
            "value": unresolved_failed_checks["total"],
            "target": 0,
        },
        "scorecard_no_fail_metrics": {
            "pass": scorecard_fail_metrics == 0,
            "value": scorecard_fail_metrics,
            "target": 0,
        },
        "warnings_absent": {
            "pass": warnings == 0,
            "value": warnings,
            "target": 0,
        },
    }

    required_gate_names = [
        "slo_1_health_window_target",
        "readiness_no_hard_failures",
        "quality_no_unresolved_failed_checks_window",
        "scorecard_no_fail_metrics",
    ]
    if strict:
        required_gate_names.append("slo_1_window_target")
        required_gate_names.append("warnings_absent")

    all_pass = all(bool(gates[name]["pass"]) for name in required_gate_names)
    severity = _classify_severity(
        hard_failures=hard_failures,
        warnings=warnings,
        failed_runs=unresolved_failed_runs["total"],
        failed_checks=unresolved_failed_checks["total"],
    )

    return {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "status": "READY" if all_pass else "NOT_READY",
        "strict": strict,
        "window_days": window_days,
        "health_window_days": health_window_days,
        "slo1_target_pct": slo1_target_pct,
        "include_blocked_as_success": include_blocked_as_success,
        "severity": severity,
        "gates": {
            **gates,
            "all_pass": all_pass,
            "required_for_status": required_gate_names,
        },
        "scorecard_status_counts": scorecard_status_counts,
        "incident_window": incident_window,
        "unresolved_failed_runs_window": unresolved_failed_runs,
        "unresolved_failed_checks_window": unresolved_failed_checks,
        "recommended_actions": _recommended_actions(
            strict=strict,
            hard_failures=hard_failures,
            warnings=warnings,
            failed_runs=unresolved_failed_runs["total"],
            failed_checks=unresolved_failed_checks["total"],
            scorecard_fail_metrics=scorecard_fail_metrics,
        ),
        "readiness": readiness,
    }
