from __future__ import annotations

from typing import Any

from pipelines.common.quality import (
    check_fact_election_result,
    check_fact_indicator,
    check_fact_indicator_source_rows,
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
            raise AssertionError("Unexpected execute call for quality check test.")
        value = self._values[self._index]
        self._index += 1
        return _ScalarResult(value)


def _default_thresholds() -> QualityThresholds:
    return QualityThresholds(
        defaults={},
        by_table={
            "fact_election_result": {"max_negative_rows": 0, "max_missing_ratio": 0.0},
            "fact_indicator": {
                "max_missing_ratio": 0.0,
                "max_source_probe_rows": 0,
                "min_rows_sidra": 1,
                "min_rows_senatran": 1,
                "min_rows_sejusp_mg": 1,
                "min_rows_siops": 1,
                "min_rows_snis": 1,
                "min_rows_inmet": 1,
                "min_rows_inpe_queimadas": 1,
                "min_rows_ana": 1,
                "min_rows_anatel": 1,
                "min_rows_aneel": 1,
            },
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


def test_check_fact_indicator_returns_five_checks_and_passes() -> None:
    # calls: total/missing for indicator_code, reference_period, value,
    # territory_id, source_probe_rows
    session = _SequenceSession([10, 0, 10, 0, 10, 0, 10, 0, 0])

    results = check_fact_indicator(session, _default_thresholds())

    assert len(results) == 5
    assert [result.name for result in results] == [
        "indicator_code_missing_ratio",
        "reference_period_missing_ratio",
        "value_missing_ratio",
        "territory_id_missing_ratio",
        "source_probe_rows",
    ]
    assert all(result.status == "pass" for result in results)


def test_check_fact_indicator_warns_when_source_probe_rows_are_present() -> None:
    # calls: total/missing for indicator_code, reference_period, value,
    # territory_id, source_probe_rows
    session = _SequenceSession([10, 1, 10, 1, 10, 1, 10, 1, 3])

    results = check_fact_indicator(session, _default_thresholds())

    by_name = {result.name: result for result in results}
    assert by_name["indicator_code_missing_ratio"].status == "fail"
    assert by_name["reference_period_missing_ratio"].status == "fail"
    assert by_name["value_missing_ratio"].status == "fail"
    assert by_name["territory_id_missing_ratio"].status == "fail"
    assert by_name["source_probe_rows"].status == "warn"


def test_check_fact_indicator_source_rows_passes_when_sources_have_minimum_rows() -> None:
    # calls: SIDRA, SENATRAN, SEJUSP_MG, SIOPS, SNIS, INMET, INPE_QUEIMADAS, ANA, ANATEL, ANEEL
    session = _SequenceSession([2, 3, 1, 4, 5, 2, 2, 1, 1, 1])

    results = check_fact_indicator_source_rows(
        session=session,
        reference_period="2025",
        thresholds=_default_thresholds(),
    )

    assert [result.name for result in results] == [
        "source_rows_sidra",
        "source_rows_senatran",
        "source_rows_sejusp_mg",
        "source_rows_siops",
        "source_rows_snis",
        "source_rows_inmet",
        "source_rows_inpe_queimadas",
        "source_rows_ana",
        "source_rows_anatel",
        "source_rows_aneel",
    ]
    assert all(result.status == "pass" for result in results)


def test_check_fact_indicator_source_rows_warns_when_source_is_below_threshold() -> None:
    # calls: SIDRA, SENATRAN, SEJUSP_MG, SIOPS, SNIS, INMET, INPE_QUEIMADAS, ANA, ANATEL, ANEEL
    session = _SequenceSession([2, 0, 1, 4, 5, 2, 2, 1, 1, 1])

    results = check_fact_indicator_source_rows(
        session=session,
        reference_period="2025",
        thresholds=_default_thresholds(),
    )

    by_name = {result.name: result for result in results}
    assert by_name["source_rows_sidra"].status == "pass"
    assert by_name["source_rows_senatran"].status == "warn"
    assert by_name["source_rows_sejusp_mg"].status == "pass"
    assert by_name["source_rows_siops"].status == "pass"
    assert by_name["source_rows_snis"].status == "pass"
    assert by_name["source_rows_inmet"].status == "pass"
    assert by_name["source_rows_inpe_queimadas"].status == "pass"
    assert by_name["source_rows_ana"].status == "pass"
    assert by_name["source_rows_anatel"].status == "pass"
    assert by_name["source_rows_aneel"].status == "pass"
