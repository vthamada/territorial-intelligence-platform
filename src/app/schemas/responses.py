from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PaginatedResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[dict[str, Any]]
