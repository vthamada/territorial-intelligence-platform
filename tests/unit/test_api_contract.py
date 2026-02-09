from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.main import app


class _FailingSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("forced-db-error")


def _fake_db() -> Generator[object, None, None]:
    yield object()


def _failing_db() -> Generator[_FailingSession, None, None]:
    yield _FailingSession()


def test_v1_health_includes_request_id_header(monkeypatch) -> None:
    monkeypatch.setattr("app.api.main.healthcheck", lambda: "ok")
    client = TestClient(app)

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}
    assert response.headers.get("x-request-id")


def test_validation_error_contract_shape() -> None:
    app.dependency_overrides[get_db] = _fake_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/geo/choropleth")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"]
    assert isinstance(payload["error"]["details"], dict)
    assert payload["error"]["request_id"]
    assert response.headers.get("x-request-id") == payload["error"]["request_id"]
    app.dependency_overrides.clear()


def test_http_error_contract_with_custom_request_id() -> None:
    app.dependency_overrides[get_db] = _fake_db
    client = TestClient(app, raise_server_exceptions=False)
    request_id = "req-contract-http-error"

    response = client.get(
        "/v1/territories?level=invalido",
        headers={"x-request-id": request_id},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "http_error"
    assert payload["error"]["request_id"] == request_id
    assert response.headers.get("x-request-id") == request_id
    app.dependency_overrides.clear()


def test_internal_error_contract_shape() -> None:
    app.dependency_overrides[get_db] = _failing_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/territories?level=municipio")

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "internal_error"
    assert payload["error"]["message"]
    assert payload["error"]["details"]["detail"] == "forced-db-error"
    assert payload["error"]["request_id"]
    assert response.headers.get("x-request-id") == payload["error"]["request_id"]
    app.dependency_overrides.clear()
