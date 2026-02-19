from __future__ import annotations

from typing import Any

from pipelines.common.quality import (
    check_fact_social_assistance_network,
    check_fact_social_protection,
)
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
            raise AssertionError("Unexpected execute call for social quality check test.")
        value = self._values[self._index]
        self._index += 1
        return _ScalarResult(value)


def _thresholds() -> QualityThresholds:
    return QualityThresholds(
        defaults={},
        by_table={
            "fact_social_protection": {
                "min_rows_after_filter": 1,
                "max_negative_rows": 0,
                "max_empty_metric_rows": 0,
            },
            "fact_social_assistance_network": {
                "min_rows_after_filter": 1,
                "max_negative_rows": 0,
                "max_empty_metric_rows": 0,
            },
        },
    )


def test_check_fact_social_protection_passes() -> None:
    # calls: rows, negative_rows, empty_metric_rows
    session = _SequenceSession([1, 0, 0])
    results = check_fact_social_protection(session, _thresholds())
    assert all(item.status == "pass" for item in results)


def test_check_fact_social_assistance_network_warns_and_fails() -> None:
    # calls: rows, negative_rows, empty_metric_rows
    session = _SequenceSession([0, 1, 1])
    results = check_fact_social_assistance_network(session, _thresholds())
    by_name = {item.name: item for item in results}
    assert by_name["social_assistance_network_rows_after_filter"].status == "warn"
    assert by_name["social_assistance_network_negative_rows"].status == "fail"
    assert by_name["social_assistance_network_empty_metric_rows"].status == "warn"
