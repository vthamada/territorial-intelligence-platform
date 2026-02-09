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


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    details = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_payload(
            code="http_error",
            message="Request failed.",
            request=request,
            details=details,
        ),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_build_error_payload(
            code="validation_error",
            message="Invalid request payload or query parameters.",
            request=request,
            details={"errors": exc.errors()},
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=_build_error_payload(
            code="internal_error",
            message="Unexpected server error.",
            request=request,
            details={"detail": str(exc)},
        ),
    )
