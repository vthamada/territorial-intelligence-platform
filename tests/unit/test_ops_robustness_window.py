from __future__ import annotations

from typing import Any

from app.ops_robustness_window import build_ops_robustness_window_report


class _ScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one(self) -> Any:
        return self._value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _RowsResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def fetchall(self) -> list[Any]:
        return self._rows


class _Executor:
    def __init__(
        self,
        *,
        historical_success_runs: int,
        failed_checks_last_window: int,
        unresolved_failed_checks: int,
        unresolved_failed_runs: int = 0,
    ) -> None:
        self.historical_success_runs = historical_success_runs
        self.failed_checks_last_window = failed_checks_last_window
        self.unresolved_failed_checks = unresolved_failed_checks
        self.unresolved_failed_runs = unresolved_failed_runs

    def execute(self, *_args: Any, **_kwargs: Any) -> _ScalarResult | _RowsResult:
        sql = str(_args[0]).lower() if _args else ""
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]

        if "from pg_extension" in sql:
            return _ScalarResult("3.5.2")
        if "from information_schema.tables" in sql:
            return _RowsResult(
                [
                    ("silver", "dim_territory"),
                    ("silver", "fact_indicator"),
                    ("silver", "fact_electorate"),
                    ("silver", "fact_election_result"),
                    ("ops", "pipeline_runs"),
                    ("ops", "pipeline_checks"),
                    ("ops", "connector_registry"),
                ]
            )
        if "from ops.connector_registry" in sql and "group by status::text" in sql:
            return _RowsResult([("implemented", 22)])
        if (
            "from ops.connector_registry" in sql
            and "select connector_name" in sql
            and "where status = 'implemented'" in sql
            and "order by connector_name" in sql
        ):
            return _RowsResult([("sidra_indicators_fetch",)])
        if "where pr.started_at_utc >= now() - make_interval(days => :window_days)" in sql and "group by pr.job_name" in sql:
            if params and int(params.get("window_days", 0)) == 7:
                return _RowsResult([("sidra_indicators_fetch", 3, 3)])
            return _RowsResult([("sidra_indicators_fetch", 10, self.historical_success_runs)])
        if "count(*)" in sql and "join implemented i on i.connector_name = pr.job_name" in sql and "join ops.pipeline_checks pc" not in sql:
            return _ScalarResult(10)
        if "count(distinct pr.run_id)" in sql:
            return _ScalarResult(10)
        if "left join ops.pipeline_checks pc on pc.run_id = pr.run_id" in sql:
            return _RowsResult([])
        if "from silver.fact_indicator" in sql and "source_probe" in sql:
            return _RowsResult([])
        if "from ops.v_data_coverage_scorecard" in sql:
            return _RowsResult([("pass", 28), ("warn", 3)])
        if "from ops.pipeline_runs" in sql and "group by status::text" in sql:
            return _RowsResult([("success", 10), ("blocked", 1)])
        if "from ops.pipeline_checks" in sql and "and status = 'fail'" in sql:
            return _ScalarResult(self.failed_checks_last_window)
        if "with checks as (" in sql and "from unresolved" in sql:
            if self.unresolved_failed_checks <= 0:
                return _RowsResult([])
            return _RowsResult(
                [
                    (
                        "dbt_build",
                        "dbt_build_execution",
                        self.unresolved_failed_checks,
                    )
                ]
            )
        if "with runs as (" in sql and "where f.status = 'failed'" in sql and "from unresolved" in sql:
            if self.unresolved_failed_runs <= 0:
                return _RowsResult([])
            return _RowsResult([("dbt_build", self.unresolved_failed_runs)])

        raise AssertionError(f"Unexpected SQL in robustness-window test: {sql}")


def test_build_ops_robustness_window_report_returns_ready_when_gates_pass() -> None:
    report = build_ops_robustness_window_report(
        _Executor(
            historical_success_runs=10,
            failed_checks_last_window=0,
            unresolved_failed_checks=0,
        ),
        window_days=30,
        health_window_days=7,
        slo1_target_pct=95.0,
        include_blocked_as_success=True,
        strict=False,
    )

    assert report["status"] == "READY"
    assert report["gates"]["all_pass"] is True
    assert report["gates"]["slo_1_health_window_target"]["pass"] is True
    assert report["gates"]["quality_no_unresolved_failed_checks_window"]["pass"] is True
    assert report["incident_window"]["failed_checks"] == 0
    assert report["unresolved_failed_runs_window"]["total"] == 0
    assert report["unresolved_failed_checks_window"]["total"] == 0
    assert report["scorecard_status_counts"]["pass"] == 28


def test_build_ops_robustness_window_report_returns_not_ready_in_strict_mode_with_warnings() -> None:
    report = build_ops_robustness_window_report(
        _Executor(
            historical_success_runs=8,
            failed_checks_last_window=0,
            unresolved_failed_checks=0,
        ),
        window_days=30,
        health_window_days=7,
        slo1_target_pct=95.0,
        include_blocked_as_success=True,
        strict=True,
    )

    assert report["status"] == "NOT_READY"
    assert report["gates"]["all_pass"] is False
    assert report["gates"]["warnings_absent"]["pass"] is False
    assert "warnings_absent" in report["gates"]["required_for_status"]


def test_build_ops_robustness_window_report_flags_unresolved_failed_checks() -> None:
    report = build_ops_robustness_window_report(
        _Executor(
            historical_success_runs=10,
            failed_checks_last_window=3,
            unresolved_failed_checks=3,
        ),
        window_days=30,
        health_window_days=7,
        slo1_target_pct=95.0,
        include_blocked_as_success=True,
        strict=False,
    )

    assert report["status"] == "NOT_READY"
    assert report["gates"]["quality_no_unresolved_failed_checks_window"]["pass"] is False
    assert report["unresolved_failed_checks_window"]["total"] == 3
