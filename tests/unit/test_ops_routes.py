from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.main import app


class _CountResult:
    def __init__(self, value: int) -> None:
        self._value = value

    def scalar_one(self) -> int:
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


def _runs_db() -> Generator[_PipelineRunsSession, None, None]:
    yield _PipelineRunsSession()


def _checks_db() -> Generator[_PipelineChecksSession, None, None]:
    yield _PipelineChecksSession()


def _connector_registry_db() -> Generator[_ConnectorRegistrySession, None, None]:
    yield _ConnectorRegistrySession()


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
