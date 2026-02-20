from __future__ import annotations

from typing import Any

from pipelines.common.quality import (
    check_fact_election_result_temporal_coverage,
    check_fact_electorate_temporal_coverage,
    check_fact_indicator_source_temporal_coverage,
    check_fact_indicator_temporal_coverage,
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
            raise AssertionError("Unexpected execute call for coverage check test.")
        value = self._values[self._index]
        self._index += 1
        return _ScalarResult(value)


def _thresholds() -> QualityThresholds:
    return QualityThresholds(
        defaults={},
        by_table={
            "fact_electorate": {
                "min_distinct_years": 2,
                "min_electoral_zone_rows": 1,
                "max_year_gap": 2,
            },
            "fact_election_result": {
                "min_distinct_years": 2,
                "min_electoral_zone_rows": 1,
                "max_year_gap": 2,
            },
            "fact_indicator": {
                "min_distinct_periods": 3,
                "min_rows_level_municipality": 1,
                "min_rows_level_district": 1,
                "min_rows_level_census_sector": 1,
                "min_source_distinct_periods_default": 2,
            },
        },
    )


def test_check_fact_electorate_temporal_coverage_passes_when_thresholds_met() -> None:
    # calls: distinct_years, zone_rows, max_year_gap
    session = _SequenceSession([2, 4, 2])
    results = check_fact_electorate_temporal_coverage(session, _thresholds())
    by_name = {result.name: result for result in results}
    assert by_name["electorate_distinct_years"].status == "pass"
    assert by_name["electorate_electoral_zone_rows"].status == "pass"
    assert by_name["electorate_max_year_gap"].status == "pass"


def test_check_fact_electorate_temporal_coverage_warns_when_below_threshold() -> None:
    # calls: distinct_years, zone_rows, max_year_gap
    session = _SequenceSession([1, 0, 4])
    results = check_fact_electorate_temporal_coverage(session, _thresholds())
    by_name = {result.name: result for result in results}
    assert by_name["electorate_distinct_years"].status == "warn"
    assert by_name["electorate_electoral_zone_rows"].status == "warn"
    assert by_name["electorate_max_year_gap"].status == "warn"


def test_check_fact_election_result_temporal_coverage_passes_when_thresholds_met() -> None:
    # calls: distinct_years, zone_rows, max_year_gap
    session = _SequenceSession([3, 8, 2])
    results = check_fact_election_result_temporal_coverage(session, _thresholds())
    by_name = {result.name: result for result in results}
    assert by_name["election_result_distinct_years"].status == "pass"
    assert by_name["election_result_electoral_zone_rows"].status == "pass"
    assert by_name["election_result_max_year_gap"].status == "pass"


def test_check_fact_indicator_temporal_coverage_warns_for_missing_levels() -> None:
    # calls: distinct_periods, municipality_rows, district_rows, census_sector_rows
    session = _SequenceSession([3, 10, 0, 0])
    results = check_fact_indicator_temporal_coverage(session, _thresholds())
    by_name = {result.name: result for result in results}
    assert by_name["indicator_distinct_periods"].status == "pass"
    assert by_name["indicator_rows_level_municipality"].status == "pass"
    assert by_name["indicator_rows_level_district"].status == "warn"
    assert by_name["indicator_rows_level_census_sector"].status == "warn"


def test_check_fact_indicator_source_temporal_coverage_warns_when_source_has_few_periods() -> None:
    # calls follow source map order:
    # DATASUS, INEP, SICONFI, MTE, TSE, SIDRA, SENATRAN, SEJUSP_MG, SIOPS, SNIS,
    # INMET, INPE_QUEIMADAS, ANA, ANATEL, ANEEL, CECAD, CENSO_SUAS
    session = _SequenceSession([2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2])
    results = check_fact_indicator_source_temporal_coverage(session, _thresholds())
    by_name = {result.name: result for result in results}
    assert by_name["source_periods_datasus"].status == "pass"
    assert by_name["source_periods_sidra"].status == "pass"
    assert by_name["source_periods_senatran"].status == "warn"
    assert by_name["source_periods_aneel"].status == "pass"
    assert by_name["source_periods_cecad"].status == "pass"
    assert by_name["source_periods_censo_suas"].status == "pass"
