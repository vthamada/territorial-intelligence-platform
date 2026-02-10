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


class _RowsResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> _RowsResult:
        return self

    def all(self) -> list[dict[str, Any]]:
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
                    "status": "partial",
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
                    {"status": "implemented", "count": 3},
                    {"status": "partial", "count": 1},
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
    assert payload["items"][0]["status"] == "partial"
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
    assert payload["connectors"]["by_status"]["partial"] == 1
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
