"""HTTP cache middleware for critical API endpoints.

Adds Cache-Control and ETag headers to cacheable GET responses.
This addresses item A07 of the traceability matrix.
"""

from __future__ import annotations

import hashlib
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

# Paths eligible for caching with their max-age in seconds.
_CACHE_RULES: list[tuple[str, int]] = [
    ("/v1/kpis/overview", 300),          # 5 min
    ("/v1/priority/list", 300),          # 5 min
    ("/v1/priority/summary", 300),       # 5 min
    ("/v1/insights/highlights", 300),    # 5 min
    ("/v1/geo/choropleth", 600),         # 10 min
    ("/v1/map/layers", 3600),            # 1 hour (static manifest)
    ("/v1/map/style-metadata", 3600),    # 1 hour (static styles)
    ("/v1/map/tiles/", 3600),            # 1 hour (MVT tiles)
    ("/v1/territory/", 300),             # 5 min (profile, compare, peers)
    ("/v1/electorate/", 600),            # 10 min
]


def _match_cache_rule(path: str) -> int | None:
    """Return max-age if path matches a cache rule, else None."""
    for prefix, max_age in _CACHE_RULES:
        if path.startswith(prefix):
            return max_age
    return None


def _compute_etag(body: bytes) -> str:
    """Compute a weak ETag from the response body."""
    digest = hashlib.md5(body, usedforsecurity=False).hexdigest()[:16]
    return f'W/"{digest}"'


class CacheHeaderMiddleware(BaseHTTPMiddleware):
    """Injects Cache-Control and ETag headers for cacheable GET endpoints."""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> StarletteResponse:
        if request.method != "GET":
            return await call_next(request)

        max_age = _match_cache_rule(request.url.path)
        if max_age is None:
            return await call_next(request)

        response: StarletteResponse = await call_next(request)

        if response.status_code != 200:
            return response

        # Collect the streaming body to compute ETag.
        body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            body_chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
        body = b"".join(body_chunks)

        etag = _compute_etag(body)

        # Support conditional requests (If-None-Match).
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match == etag:
            return Response(
                status_code=304,
                headers={
                    "ETag": etag,
                    "Cache-Control": f"public, max-age={max_age}",
                },
            )

        return Response(
            content=body,
            status_code=response.status_code,
            headers={
                **dict(response.headers),
                "Cache-Control": f"public, max-age={max_age}",
                "ETag": etag,
            },
            media_type=response.media_type,
        )
