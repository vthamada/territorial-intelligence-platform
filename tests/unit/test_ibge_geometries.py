from __future__ import annotations

from typing import Any

from pipelines.ibge_geometries import _upsert_geometry_area_indicators


class _FakeResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _FakeSession:
    def __init__(self, rowcounts: list[int]) -> None:
        self._rowcounts = rowcounts
        self.params_seen: list[dict[str, Any]] = []

    def execute(self, _statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        if not self._rowcounts:
            raise AssertionError("Unexpected execute call.")
        self.params_seen.append(params or {})
        return _FakeResult(self._rowcounts.pop(0))


def test_upsert_geometry_area_indicators_returns_rows_by_level() -> None:
    session = _FakeSession([1, 4, 11])
    counts = _upsert_geometry_area_indicators(
        session=session,
        municipality_ibge_code="3121605",
        reference_period="2025",
    )

    assert counts == {
        "municipality": 1,
        "district": 4,
        "census_sector": 11,
    }
    assert [item["level"] for item in session.params_seen] == [
        "municipality",
        "district",
        "census_sector",
    ]
