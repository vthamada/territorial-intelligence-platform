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

    hard_failures = int(len(readiness.get("hard_failures", [])))
    warnings = int(len(readiness.get("warnings", [])))
    scorecard_fail_metrics = int(scorecard_status_counts.get("fail", 0))

    gates = {
        "slo_1_window_target": {
            "pass": bool(readiness.get("slo1", {}).get("meets_target")),
            "value": readiness.get("slo1", {}).get("success_rate_pct"),
            "target": slo1_target_pct,
        },
        "readiness_no_hard_failures": {
            "pass": hard_failures == 0,
            "value": hard_failures,
            "target": 0,
        },
        "quality_no_failed_checks_window": {
            "pass": incident_window["failed_checks"] == 0,
            "value": incident_window["failed_checks"],
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
        "slo_1_window_target",
        "readiness_no_hard_failures",
        "quality_no_failed_checks_window",
        "scorecard_no_fail_metrics",
    ]
    if strict:
        required_gate_names.append("warnings_absent")

    all_pass = all(bool(gates[name]["pass"]) for name in required_gate_names)
    severity = _classify_severity(
        hard_failures=hard_failures,
        warnings=warnings,
        failed_runs=incident_window["failed_runs"],
        failed_checks=incident_window["failed_checks"],
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
        "recommended_actions": _recommended_actions(
            strict=strict,
            hard_failures=hard_failures,
            warnings=warnings,
            failed_runs=incident_window["failed_runs"],
            failed_checks=incident_window["failed_checks"],
            scorecard_fail_metrics=scorecard_fail_metrics,
        ),
        "readiness": readiness,
    }
