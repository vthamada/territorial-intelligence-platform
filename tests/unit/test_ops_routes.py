from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.main import app


class _CountResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one(self) -> Any:
        return self._value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _RowsResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def mappings(self) -> _RowsResult:
        return self

    def all(self) -> list[Any]:
        return self._rows

    def fetchall(self) -> list[Any]:
        return self._rows


class _PipelineRunsSession:
    def __init__(self) -> None:
        self._execute_calls = 0
        self.last_params: dict[str, Any] | None = None

    def execute(self, *_args: Any, **_kwargs: Any) -> _CountResult | _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        if isinstance(params, dict):
            self.last_params = params
        self._execute_calls += 1
        if self._execute_calls == 1:
            return _CountResult(1)
        return _RowsResult(
            [
                {
                    "run_id": "11111111-1111-1111-1111-111111111111",
                    "job_name": "labor_mte_fetch",
                    "source": "MTE",
                    "dataset": "mte_novo_caged",
                    "wave": "MVP-3",
                    "reference_period": "2024",
                    "started_at_utc": "2026-02-10T10:00:00+00:00",
                    "finished_at_utc": "2026-02-10T10:01:00+00:00",
                    "duration_seconds": 60,
                    "status": "success",
                    "rows_extracted": 10,
                    "rows_loaded": 4,
                    "warnings_count": 0,
                    "errors_count": 0,
                    "bronze_path": "data/bronze/MTE/...",
                    "manifest_path": "data/manifests/MTE/...",
                    "checksum_sha256": "abc",
                    "details": {"source_type": "ftp"},
                }
            ]
        )


class _PipelineChecksSession:
    def __init__(self) -> None:
        self._execute_calls = 0
        self.last_params: dict[str, Any] | None = None

    def execute(self, *_args: Any, **_kwargs: Any) -> _CountResult | _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        if isinstance(params, dict):
            self.last_params = params
        self._execute_calls += 1
        if self._execute_calls == 1:
            return _CountResult(1)
        return _RowsResult(
            [
                {
                    "check_id": 1,
                    "run_id": "11111111-1111-1111-1111-111111111111",
                    "job_name": "labor_mte_fetch",
                    "source": "MTE",
                    "dataset": "mte_novo_caged",
                    "wave": "MVP-3",
                    "reference_period": "2024",
                    "check_name": "mte_data_source_resolved",
                    "status": "pass",
                    "details": "MTE dataset loaded from ftp.",
                    "observed_value": 1,
                    "threshold_value": 1,
                    "created_at_utc": "2026-02-10T10:01:00+00:00",
                }
            ]
        )


class _ConnectorRegistrySession:
    def __init__(self) -> None:
        self._execute_calls = 0
        self.last_params: dict[str, Any] | None = None

    def execute(self, *_args: Any, **_kwargs: Any) -> _CountResult | _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        if isinstance(params, dict):
            self.last_params = params
        self._execute_calls += 1
        if self._execute_calls == 1:
            return _CountResult(1)
        return _RowsResult(
            [
                {
                    "connector_name": "labor_mte_fetch",
                    "source": "MTE",
                    "wave": "MVP-3",
                    "status": "implemented",
                    "notes": "FTP first + manual fallback",
                    "updated_at_utc": "2026-02-10T12:00:00+00:00",
                }
            ]
        )


class _OpsSummarySession:
    def __init__(self) -> None:
        self.last_params: dict[str, Any] | None = None

    def execute(self, *_args: Any, **_kwargs: Any) -> _CountResult | _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        if isinstance(params, dict):
            self.last_params = params

        sql = str(_args[0]).lower() if _args else ""

        if "from ops.pipeline_runs pr" in sql and "group by pr.status" in sql:
            return _RowsResult(
                [
                    {"status": "fail", "count": 1},
                    {"status": "success", "count": 2},
                ]
            )
        if "from ops.pipeline_runs pr" in sql and "group by coalesce(pr.wave, 'unknown')" in sql:
            return _RowsResult([{"wave": "MVP-3", "count": 3}])
        if "from ops.pipeline_runs pr" in sql and "max(pr.started_at_utc)" in sql:
            return _CountResult(datetime(2026, 2, 10, 10, 2, tzinfo=UTC))
        if "from ops.pipeline_runs pr" in sql and "count(*)" in sql:
            return _CountResult(3)

        if "from ops.pipeline_checks pc" in sql and "group by pc.status" in sql:
            return _RowsResult(
                [
                    {"status": "fail", "count": 1},
                    {"status": "pass", "count": 4},
                ]
            )
        if "from ops.pipeline_checks pc" in sql and "max(pc.created_at_utc)" in sql:
            return _CountResult(datetime(2026, 2, 10, 10, 3, tzinfo=UTC))
        if "from ops.pipeline_checks pc" in sql and "count(*)" in sql:
            return _CountResult(5)

        if "from ops.connector_registry cr" in sql and "group by cr.status::text" in sql:
            return _RowsResult(
                [
                    {"status": "implemented", "count": 4},
                ]
            )
        if "from ops.connector_registry cr" in sql and "group by cr.wave" in sql:
            return _RowsResult(
                [
                    {"wave": "MVP-2", "count": 2},
                    {"wave": "MVP-3", "count": 2},
                ]
            )
        if "from ops.connector_registry cr" in sql and "max(cr.updated_at_utc)" in sql:
            return _CountResult(datetime(2026, 2, 10, 12, 0, tzinfo=UTC))
        if "from ops.connector_registry cr" in sql and "count(*)" in sql:
            return _CountResult(4)

        raise AssertionError(f"Unexpected SQL in summary test: {sql}")


class _OpsTimeseriesSession:
    def __init__(self) -> None:
        self.last_params: dict[str, Any] | None = None

    def execute(self, *_args: Any, **_kwargs: Any) -> _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        if isinstance(params, dict):
            self.last_params = params

        sql = str(_args[0]).lower() if _args else ""
        if "from ops.pipeline_runs pr" in sql:
            return _RowsResult(
                [
                    {
                        "bucket_start_utc": datetime(2026, 2, 9, 0, 0, tzinfo=UTC),
                        "status": "fail",
                        "count": 1,
                    },
                    {
                        "bucket_start_utc": datetime(2026, 2, 9, 0, 0, tzinfo=UTC),
                        "status": "success",
                        "count": 2,
                    },
                    {
                        "bucket_start_utc": datetime(2026, 2, 10, 0, 0, tzinfo=UTC),
                        "status": "success",
                        "count": 3,
                    },
                ]
            )
        if "from ops.pipeline_checks pc" in sql:
            return _RowsResult(
                [
                    {
                        "bucket_start_utc": datetime(2026, 2, 9, 10, 0, tzinfo=UTC),
                        "status": "pass",
                        "count": 4,
                    },
                    {
                        "bucket_start_utc": datetime(2026, 2, 9, 10, 0, tzinfo=UTC),
                        "status": "fail",
                        "count": 1,
                    },
                    {
                        "bucket_start_utc": datetime(2026, 2, 9, 11, 0, tzinfo=UTC),
                        "status": "pass",
                        "count": 2,
                    },
                ]
            )
        raise AssertionError(f"Unexpected SQL in timeseries test: {sql}")


class _OpsSlaSession:
    def __init__(self) -> None:
        self.last_params: dict[str, Any] | None = None

    def execute(self, *_args: Any, **_kwargs: Any) -> _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        if isinstance(params, dict):
            self.last_params = params

        return _RowsResult(
            [
                {
                    "job_name": "education_inep_fetch",
                    "source": "INEP",
                    "dataset": "inep_sinopse",
                    "wave": "MVP-3",
                    "total_runs": 4,
                    "successful_runs": 3,
                    "success_rate": 0.75,
                    "p95_duration_seconds": 80.0,
                    "avg_duration_seconds": 60.0,
                    "latest_started_at_utc": datetime(2026, 2, 10, 10, 0, tzinfo=UTC),
                },
                {
                    "job_name": "labor_mte_fetch",
                    "source": "MTE",
                    "dataset": "mte_novo_caged",
                    "wave": "MVP-3",
                    "total_runs": 2,
                    "successful_runs": 1,
                    "success_rate": 0.5,
                    "p95_duration_seconds": 120.0,
                    "avg_duration_seconds": 90.0,
                    "latest_started_at_utc": datetime(2026, 2, 10, 12, 0, tzinfo=UTC),
                },
            ]
        )


class _OpsSourceCoverageSession:
    def __init__(self) -> None:
        self.last_params: dict[str, Any] | None = None

    def execute(self, *_args: Any, **_kwargs: Any) -> _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        if isinstance(params, dict):
            self.last_params = params

        return _RowsResult(
            [
                {
                    "source": "MTE",
                    "wave": "MVP-3",
                    "implemented_connectors": 1,
                    "runs_total": 4,
                    "runs_success": 1,
                    "runs_blocked": 3,
                    "runs_failed": 0,
                    "rows_loaded_total": 4,
                    "latest_run_started_at_utc": datetime(2026, 2, 11, 12, 0, tzinfo=UTC),
                    "latest_reference_period": "2025",
                    "fact_indicator_rows": 4,
                    "fact_indicator_codes": 1,
                    "latest_indicator_updated_at": datetime(2026, 2, 11, 12, 1, tzinfo=UTC),
                    "coverage_status": "ready",
                },
                {
                    "source": "SNIS",
                    "wave": "MVP-4",
                    "implemented_connectors": 1,
                    "runs_total": 2,
                    "runs_success": 0,
                    "runs_blocked": 2,
                    "runs_failed": 0,
                    "rows_loaded_total": 0,
                    "latest_run_started_at_utc": datetime(2026, 2, 11, 12, 5, tzinfo=UTC),
                    "latest_reference_period": "2025",
                    "fact_indicator_rows": 0,
                    "fact_indicator_codes": 0,
                    "latest_indicator_updated_at": None,
                    "coverage_status": "blocked",
                },
            ]
        )


class _OpsReadinessSession:
    def __init__(self) -> None:
        self.last_params: dict[str, Any] | None = None
        self.params_history: list[dict[str, Any]] = []

    def execute(self, *_args: Any, **_kwargs: Any) -> _CountResult | _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        if isinstance(params, dict):
            self.last_params = params
            self.params_history.append(dict(params))

        sql = str(_args[0]).lower() if _args else ""

        if "from pg_extension" in sql:
            return _CountResult("3.5.2")
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
        if "where pr.started_at_utc >= now() - make_interval(days => :window_days)" in sql and "group by pr.job_name" in sql:
            if params and params.get("window_days") == 1:
                return _RowsResult([("sidra_indicators_fetch", 3, 3)])
            return _RowsResult([("sidra_indicators_fetch", 10, 8)])
        if (
            "from ops.connector_registry" in sql
            and "select connector_name" in sql
            and "where status = 'implemented'" in sql
            and "order by connector_name" in sql
        ):
            return _RowsResult([("sidra_indicators_fetch",)])
        if "count(*)" in sql and "join implemented i on i.connector_name = pr.job_name" in sql and "join ops.pipeline_checks pc" not in sql:
            return _CountResult(10)
        if "count(distinct pr.run_id)" in sql:
            return _CountResult(10)
        if "left join ops.pipeline_checks pc on pc.run_id = pr.run_id" in sql:
            return _RowsResult([])
        if "from silver.fact_indicator" in sql and "source_probe" in sql:
            return _RowsResult([])

        raise AssertionError(f"Unexpected SQL in readiness test: {sql}")


class _FrontendEventsIngestSession:
    def __init__(self) -> None:
        self.last_params: dict[str, Any] | None = None

    def execute(self, *_args: Any, **_kwargs: Any) -> _CountResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        if isinstance(params, dict):
            self.last_params = params
        return _CountResult(123)


class _FrontendEventsListSession:
    def __init__(self) -> None:
        self._execute_calls = 0
        self.last_params: dict[str, Any] | None = None

    def execute(self, *_args: Any, **_kwargs: Any) -> _CountResult | _RowsResult:
        params = _kwargs.get("params")
        if params is None and len(_args) >= 2 and isinstance(_args[1], dict):
            params = _args[1]
        if isinstance(params, dict):
            self.last_params = params
        self._execute_calls += 1
        if self._execute_calls == 1:
            return _CountResult(1)
        return _RowsResult(
            [
                {
                    "event_id": 123,
                    "category": "api_request",
                    "name": "api_request_failed",
                    "severity": "error",
                    "attributes": {"status": 500},
                    "event_timestamp_utc": datetime(2026, 2, 11, 18, 0, tzinfo=UTC),
                    "received_at_utc": datetime(2026, 2, 11, 18, 0, 1, tzinfo=UTC),
                    "request_id": "req-123",
                    "user_agent": "vitest",
                }
            ]
        )


def _runs_db() -> Generator[_PipelineRunsSession, None, None]:
    yield _PipelineRunsSession()


def _checks_db() -> Generator[_PipelineChecksSession, None, None]:
    yield _PipelineChecksSession()


def _connector_registry_db() -> Generator[_ConnectorRegistrySession, None, None]:
    yield _ConnectorRegistrySession()


def _summary_db() -> Generator[_OpsSummarySession, None, None]:
    yield _OpsSummarySession()


def _timeseries_db() -> Generator[_OpsTimeseriesSession, None, None]:
    yield _OpsTimeseriesSession()


def _sla_db() -> Generator[_OpsSlaSession, None, None]:
    yield _OpsSlaSession()


def _source_coverage_db() -> Generator[_OpsSourceCoverageSession, None, None]:
    yield _OpsSourceCoverageSession()


def _readiness_db() -> Generator[_OpsReadinessSession, None, None]:
    yield _OpsReadinessSession()


def _frontend_events_ingest_db() -> Generator[_FrontendEventsIngestSession, None, None]:
    yield _FrontendEventsIngestSession()


def _frontend_events_list_db() -> Generator[_FrontendEventsListSession, None, None]:
    yield _FrontendEventsListSession()


def test_pipeline_runs_endpoint_returns_paginated_payload() -> None:
    app.dependency_overrides[get_db] = _runs_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/pipeline-runs?page=1&page_size=10&job_name=labor_mte_fetch")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["job_name"] == "labor_mte_fetch"
    app.dependency_overrides.clear()


def test_pipeline_runs_endpoint_accepts_started_range_filters() -> None:
    session = _PipelineRunsSession()

    def _db() -> Generator[_PipelineRunsSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/v1/ops/pipeline-runs"
        "?started_from=2026-02-10T00:00:00Z"
        "&started_to=2026-02-10T23:59:59Z"
    )

    assert response.status_code == 200
    assert session.last_params is not None
    assert session.last_params["started_from"] == datetime(2026, 2, 10, 0, 0, tzinfo=UTC)
    assert session.last_params["started_to"] == datetime(2026, 2, 10, 23, 59, 59, tzinfo=UTC)
    app.dependency_overrides.clear()


def test_pipeline_runs_endpoint_accepts_run_status_alias() -> None:
    session = _PipelineRunsSession()

    def _db() -> Generator[_PipelineRunsSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/pipeline-runs?run_status=success")

    assert response.status_code == 200
    assert session.last_params is not None
    assert session.last_params["status"] == "success"
    app.dependency_overrides.clear()


def test_pipeline_runs_endpoint_prefers_run_status_over_status() -> None:
    session = _PipelineRunsSession()

    def _db() -> Generator[_PipelineRunsSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/pipeline-runs?status=failed&run_status=success")

    assert response.status_code == 200
    assert session.last_params is not None
    assert session.last_params["status"] == "success"
    app.dependency_overrides.clear()


def test_pipeline_checks_endpoint_returns_paginated_payload() -> None:
    app.dependency_overrides[get_db] = _checks_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/v1/ops/pipeline-checks?page=1&page_size=10&run_id=11111111-1111-1111-1111-111111111111"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["check_name"] == "mte_data_source_resolved"
    app.dependency_overrides.clear()


def test_pipeline_checks_endpoint_accepts_created_range_filters() -> None:
    session = _PipelineChecksSession()

    def _db() -> Generator[_PipelineChecksSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/v1/ops/pipeline-checks"
        "?created_from=2026-02-10T00:00:00Z"
        "&created_to=2026-02-10T23:59:59Z"
    )

    assert response.status_code == 200
    assert session.last_params is not None
    assert session.last_params["created_from"] == datetime(2026, 2, 10, 0, 0, tzinfo=UTC)
    assert session.last_params["created_to"] == datetime(2026, 2, 10, 23, 59, 59, tzinfo=UTC)
    app.dependency_overrides.clear()


def test_connector_registry_endpoint_returns_paginated_payload() -> None:
    app.dependency_overrides[get_db] = _connector_registry_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/connector-registry?page=1&page_size=10&wave=MVP-3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["connector_name"] == "labor_mte_fetch"
    assert payload["items"][0]["status"] == "implemented"
    app.dependency_overrides.clear()


def test_connector_registry_endpoint_accepts_updated_range_filters() -> None:
    session = _ConnectorRegistrySession()

    def _db() -> Generator[_ConnectorRegistrySession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/v1/ops/connector-registry"
        "?updated_from=2026-02-10T00:00:00Z"
        "&updated_to=2026-02-10T23:59:59Z"
    )

    assert response.status_code == 200
    assert session.last_params is not None
    assert session.last_params["updated_from"] == datetime(2026, 2, 10, 0, 0, tzinfo=UTC)
    assert session.last_params["updated_to"] == datetime(2026, 2, 10, 23, 59, 59, tzinfo=UTC)
    app.dependency_overrides.clear()


def test_pipeline_runs_endpoint_rejects_invalid_started_from() -> None:
    app.dependency_overrides[get_db] = _runs_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/pipeline-runs?started_from=not-a-date")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    app.dependency_overrides.clear()


def test_frontend_events_ingest_endpoint_accepts_payload() -> None:
    session = _FrontendEventsIngestSession()

    def _db() -> Generator[_FrontendEventsIngestSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/v1/ops/frontend-events",
        json={
            "category": "api_request",
            "name": "api_request_failed",
            "severity": "error",
            "attributes": {"status": 500},
            "timestamp_utc": "2026-02-11T18:00:00Z",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "accepted"
    assert payload["event_id"] == 123
    assert session.last_params is not None
    assert session.last_params["category"] == "api_request"
    assert session.last_params["severity"] == "error"
    assert session.last_params["event_timestamp_utc"] == datetime(2026, 2, 11, 18, 0, tzinfo=UTC)
    assert session.last_params["request_id"] is not None
    app.dependency_overrides.clear()


def test_frontend_events_endpoint_returns_paginated_payload() -> None:
    app.dependency_overrides[get_db] = _frontend_events_list_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/frontend-events?page=1&page_size=10&category=api_request")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["event_id"] == 123
    assert payload["items"][0]["category"] == "api_request"
    app.dependency_overrides.clear()


def test_frontend_events_endpoint_accepts_temporal_filters() -> None:
    session = _FrontendEventsListSession()

    def _db() -> Generator[_FrontendEventsListSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/v1/ops/frontend-events"
        "?severity=error"
        "&event_from=2026-02-11T00:00:00Z"
        "&event_to=2026-02-11T23:59:59Z"
    )

    assert response.status_code == 200
    assert session.last_params is not None
    assert session.last_params["severity"] == "error"
    assert session.last_params["event_from"] == datetime(2026, 2, 11, 0, 0, tzinfo=UTC)
    assert session.last_params["event_to"] == datetime(2026, 2, 11, 23, 59, 59, tzinfo=UTC)
    app.dependency_overrides.clear()


def test_ops_summary_endpoint_returns_aggregated_payload() -> None:
    app.dependency_overrides[get_db] = _summary_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/summary?wave=MVP-3&reference_period=2024")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runs"]["total"] == 3
    assert payload["runs"]["by_status"]["success"] == 2
    assert payload["runs"]["by_wave"]["MVP-3"] == 3
    assert payload["checks"]["total"] == 5
    assert payload["checks"]["by_status"]["fail"] == 1
    assert payload["connectors"]["total"] == 4
    assert payload["connectors"]["by_status"]["implemented"] == 4
    app.dependency_overrides.clear()


def test_ops_summary_endpoint_accepts_temporal_and_status_filters() -> None:
    session = _OpsSummarySession()

    def _db() -> Generator[_OpsSummarySession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/v1/ops/summary"
        "?run_status=success"
        "&check_status=pass"
        "&connector_status=implemented"
        "&started_from=2026-02-10T00:00:00Z"
        "&created_from=2026-02-10T00:00:00Z"
        "&updated_from=2026-02-10T00:00:00Z"
    )

    assert response.status_code == 200
    assert session.last_params is not None
    assert session.last_params["run_status"] == "success"
    assert session.last_params["check_status"] == "pass"
    assert session.last_params["connector_status"] == "implemented"
    assert session.last_params["started_from"] == datetime(2026, 2, 10, 0, 0, tzinfo=UTC)
    assert session.last_params["created_from"] == datetime(2026, 2, 10, 0, 0, tzinfo=UTC)
    assert session.last_params["updated_from"] == datetime(2026, 2, 10, 0, 0, tzinfo=UTC)
    app.dependency_overrides.clear()


def test_ops_summary_endpoint_rejects_invalid_started_from() -> None:
    app.dependency_overrides[get_db] = _summary_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/summary?started_from=not-a-date")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    app.dependency_overrides.clear()


def test_ops_sla_endpoint_returns_aggregated_payload() -> None:
    app.dependency_overrides[get_db] = _sla_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/sla?wave=MVP-3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["include_blocked_as_success"] is False
    assert payload["min_total_runs"] == 1
    assert len(payload["items"]) == 2
    assert payload["items"][0]["job_name"] == "education_inep_fetch"
    assert payload["items"][0]["success_rate"] == 0.75
    app.dependency_overrides.clear()


def test_ops_sla_endpoint_accepts_filters() -> None:
    session = _OpsSlaSession()

    def _db() -> Generator[_OpsSlaSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/v1/ops/sla"
        "?job_name=labor_mte_fetch"
        "&run_status=success"
        "&started_from=2026-02-10T00:00:00Z"
        "&include_blocked_as_success=true"
        "&min_total_runs=2"
    )

    assert response.status_code == 200
    assert session.last_params is not None
    assert session.last_params["job_name"] == "labor_mte_fetch"
    assert session.last_params["run_status"] == "success"
    assert session.last_params["include_blocked_as_success"] is True
    assert session.last_params["min_total_runs"] == 2
    assert session.last_params["started_from"] == datetime(2026, 2, 10, 0, 0, tzinfo=UTC)
    app.dependency_overrides.clear()


def test_ops_sla_endpoint_rejects_invalid_min_total_runs() -> None:
    app.dependency_overrides[get_db] = _sla_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/sla?min_total_runs=0")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    app.dependency_overrides.clear()


def test_ops_source_coverage_endpoint_returns_aggregated_payload() -> None:
    app.dependency_overrides[get_db] = _source_coverage_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/source-coverage")

    assert response.status_code == 200
    payload = response.json()
    assert payload["include_internal"] is False
    assert len(payload["items"]) == 2
    assert payload["items"][0]["source"] == "MTE"
    assert payload["items"][0]["fact_indicator_rows"] == 4
    assert payload["items"][0]["coverage_status"] == "ready"
    assert payload["items"][1]["source"] == "SNIS"
    assert payload["items"][1]["coverage_status"] == "blocked"
    app.dependency_overrides.clear()


def test_ops_source_coverage_endpoint_accepts_filters() -> None:
    session = _OpsSourceCoverageSession()

    def _db() -> Generator[_OpsSourceCoverageSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/v1/ops/source-coverage"
        "?source=MTE"
        "&wave=MVP-3"
        "&reference_period=2025"
        "&include_internal=true"
        "&started_from=2026-02-10T00:00:00Z"
    )

    assert response.status_code == 200
    assert session.last_params is not None
    assert session.last_params["source"] == "MTE"
    assert session.last_params["wave"] == "MVP-3"
    assert session.last_params["reference_period"] == "2025"
    assert session.last_params["include_internal"] is True
    assert session.last_params["started_from"] == datetime(2026, 2, 10, 0, 0, tzinfo=UTC)
    app.dependency_overrides.clear()


def test_ops_readiness_endpoint_returns_operational_snapshot() -> None:
    app.dependency_overrides[get_db] = _readiness_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "READY"
    assert payload["postgis"]["installed"] is True
    assert payload["required_tables"]["missing"] == []
    assert payload["connector_registry"]["total"] == 22
    assert payload["slo1"]["window_days"] == 7
    assert payload["slo1_current"]["window_days"] == 1
    assert payload["slo3"]["runs_missing_checks"] == 0
    assert isinstance(payload["warnings"], list)
    app.dependency_overrides.clear()


def test_ops_readiness_endpoint_accepts_custom_windows_and_strict_mode() -> None:
    session = _OpsReadinessSession()

    def _db() -> Generator[_OpsReadinessSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/v1/ops/readiness"
        "?window_days=14"
        "&health_window_days=2"
        "&slo1_target_pct=90"
        "&strict=true"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "NOT_READY"
    assert payload["strict"] is True
    assert any(item.get("window_days") == 14 for item in session.params_history)
    assert any(item.get("window_days") == 2 for item in session.params_history)
    app.dependency_overrides.clear()


def test_ops_timeseries_runs_endpoint_returns_bucketed_payload() -> None:
    app.dependency_overrides[get_db] = _timeseries_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/timeseries?entity=runs&granularity=day")

    assert response.status_code == 200
    payload = response.json()
    assert payload["entity"] == "runs"
    assert payload["granularity"] == "day"
    assert len(payload["items"]) == 2
    assert payload["items"][0]["total"] == 3
    assert payload["items"][0]["by_status"]["fail"] == 1
    assert payload["items"][0]["by_status"]["success"] == 2
    assert payload["items"][1]["total"] == 3
    app.dependency_overrides.clear()


def test_ops_timeseries_checks_endpoint_accepts_filters() -> None:
    session = _OpsTimeseriesSession()

    def _db() -> Generator[_OpsTimeseriesSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = _db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/v1/ops/timeseries"
        "?entity=checks"
        "&granularity=hour"
        "&run_status=success"
        "&check_status=pass"
        "&created_from=2026-02-09T00:00:00Z"
    )

    assert response.status_code == 200
    assert session.last_params is not None
    assert session.last_params["run_status"] == "success"
    assert session.last_params["check_status"] == "pass"
    assert session.last_params["created_from"] == datetime(2026, 2, 9, 0, 0, tzinfo=UTC)

    payload = response.json()
    assert payload["entity"] == "checks"
    assert payload["granularity"] == "hour"
    assert payload["items"][0]["total"] == 5
    app.dependency_overrides.clear()


def test_ops_timeseries_endpoint_rejects_invalid_entity() -> None:
    app.dependency_overrides[get_db] = _timeseries_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/ops/timeseries?entity=invalid")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    app.dependency_overrides.clear()
