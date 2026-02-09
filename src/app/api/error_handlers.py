from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _build_error_payload(
    *,
    code: str,
    message: str,
    request: Request,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": getattr(request.state, "request_id", None),
        }
    }


def _error_response(*, status_code: int, payload: dict[str, Any], request: Request) -> JSONResponse:
    response = JSONResponse(status_code=status_code, content=payload)
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        response.headers["x-request-id"] = request_id
    return response


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    details = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
    return _error_response(
        status_code=exc.status_code,
        payload=_build_error_payload(
            code="http_error",
            message="Request failed.",
            request=request,
            details=details,
        ),
        request=request,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _error_response(
        status_code=422,
        payload=_build_error_payload(
            code="validation_error",
            message="Invalid request payload or query parameters.",
            request=request,
            details={"errors": exc.errors()},
        ),
        request=request,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(
        status_code=500,
        payload=_build_error_payload(
            code="internal_error",
            message="Unexpected server error.",
            request=request,
            details={"detail": str(exc)},
        ),
        request=request,
    )
