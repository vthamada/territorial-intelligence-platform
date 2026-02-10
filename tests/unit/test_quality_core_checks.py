from __future__ import annotations

from typing import Any

from pipelines.common.quality import check_fact_election_result, check_fact_indicator
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
            raise AssertionError("Unexpected execute call for quality check test.")
        value = self._values[self._index]
        self._index += 1
        return _ScalarResult(value)


def _default_thresholds() -> QualityThresholds:
    return QualityThresholds(
        defaults={},
        by_table={
            "fact_election_result": {"max_negative_rows": 0, "max_missing_ratio": 0.0},
            "fact_indicator": {"max_missing_ratio": 0.0},
        },
    )


def test_check_fact_election_result_returns_three_checks_and_passes() -> None:
    # calls: negative_count, total_year, missing_year, total_territory, missing_territory
    session = _SequenceSession([0, 10, 0, 10, 0])

    results = check_fact_election_result(session, _default_thresholds())

    assert len(results) == 3
    assert [result.name for result in results] == [
        "result_non_negative",
        "election_year_missing_ratio",
        "territory_id_missing_ratio",
    ]
    assert all(result.status == "pass" for result in results)


def test_check_fact_election_result_fails_when_thresholds_are_violated() -> None:
    # calls: negative_count, total_year, missing_year, total_territory, missing_territory
    session = _SequenceSession([1, 10, 1, 10, 1])

    results = check_fact_election_result(session, _default_thresholds())

    by_name = {result.name: result for result in results}
    assert by_name["result_non_negative"].status == "fail"
    assert by_name["election_year_missing_ratio"].status == "fail"
    assert by_name["territory_id_missing_ratio"].status == "fail"


def test_check_fact_indicator_returns_four_checks_and_passes() -> None:
    # calls: total/missing for indicator_code, reference_period, value, territory_id
    session = _SequenceSession([10, 0, 10, 0, 10, 0, 10, 0])

    results = check_fact_indicator(session, _default_thresholds())

    assert len(results) == 4
    assert [result.name for result in results] == [
        "indicator_code_missing_ratio",
        "reference_period_missing_ratio",
        "value_missing_ratio",
        "territory_id_missing_ratio",
    ]
    assert all(result.status == "pass" for result in results)


def test_check_fact_indicator_fails_when_thresholds_are_violated() -> None:
    # calls: total/missing for indicator_code, reference_period, value, territory_id
    session = _SequenceSession([10, 1, 10, 1, 10, 1, 10, 1])

    results = check_fact_indicator(session, _default_thresholds())

    assert all(result.status == "fail" for result in results)
