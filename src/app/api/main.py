from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.error_handlers import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.api.routes_elections import router as elections_router
from app.api.routes_electorate import router as electorate_router
from app.api.routes_geo import router as geo_router
from app.api.routes_indicators import router as indicators_router
from app.api.routes_territories import router as territories_router
from app.db import healthcheck
from app.logging import configure_logging
from app.settings import get_settings

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name)
api_v1_router = APIRouter(prefix=settings.api_version_prefix)
api_v1_router.include_router(territories_router)
api_v1_router.include_router(indicators_router)
api_v1_router.include_router(electorate_router)
api_v1_router.include_router(elections_router)
api_v1_router.include_router(geo_router)
app.include_router(api_v1_router)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.get(f"{settings.api_version_prefix}/health")
def get_v1_health() -> dict:
    return {"status": "ok", "db": healthcheck()}


@app.get("/health", include_in_schema=False)
def get_health_compat() -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "db": healthcheck(),
            "deprecated": True,
            "message": f"Use {settings.api_version_prefix}/health instead.",
        },
    )
