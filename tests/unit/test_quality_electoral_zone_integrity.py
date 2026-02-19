from __future__ import annotations

from typing import Any

from pipelines.common.quality import check_dim_territory_electoral_zone_integrity
from pipelines.common.quality_thresholds import QualityThresholds


class _ScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one(self) -> Any:
        return self._value


class _SequenceSession:
    def __init__(self, values: list[Any]) -> None:
        self._values = values
        self._index = 0

    def execute(self, _statement: Any, _params: dict[str, Any] | None = None) -> _ScalarResult:
        if self._index >= len(self._values):
            raise AssertionError("Unexpected execute call for electoral zone integrity check.")
        value = self._values[self._index]
        self._index += 1
        return _ScalarResult(value)


def _thresholds() -> QualityThresholds:
    return QualityThresholds(
        defaults={},
        by_table={
            "dim_territory": {
                "min_electoral_zone_count": 1,
                "max_electoral_zone_orphans": 0,
                "max_electoral_zone_missing_canonical_key": 0,
            }
        },
    )


def test_check_dim_territory_electoral_zone_integrity_passes() -> None:
    # calls: zone_count, orphans, missing_canonical
    session = _SequenceSession([2, 0, 0])
    results = check_dim_territory_electoral_zone_integrity(
        session=session,
        municipality_code="3121605",
        thresholds=_thresholds(),
    )
    assert all(item.status == "pass" for item in results)


def test_check_dim_territory_electoral_zone_integrity_warns_or_fails() -> None:
    # calls: zone_count, orphans, missing_canonical
    session = _SequenceSession([0, 1, 1])
    results = check_dim_territory_electoral_zone_integrity(
        session=session,
        municipality_code="3121605",
        thresholds=_thresholds(),
    )
    by_name = {item.name: item for item in results}
    assert by_name["electoral_zone_count"].status == "warn"
    assert by_name["electoral_zone_orphans"].status == "fail"
    assert by_name["electoral_zone_missing_canonical_key"].status == "fail"
