from __future__ import annotations

from pipelines.common.source_probe import (
    _extract_html_probe_value,
    _extract_numeric_probe_value,
    _status_from_min_threshold,
)


def test_extract_numeric_probe_value_from_items_list() -> None:
    payload = {"items": [{"id": 1}, {"id": 2}, {"id": 3}]}
    assert _extract_numeric_probe_value(payload) == 3


def test_extract_numeric_probe_value_from_ckan_results() -> None:
    payload = {"result": {"results": [{"name": "a"}, {"name": "b"}]}}
    assert _extract_numeric_probe_value(payload) == 2


def test_extract_html_probe_value_counts_anchor_tags() -> None:
    html = "<html><a href='x'>x</a><div></div><a href='y'>y</a></html>"
    assert _extract_html_probe_value(html) == 2


def test_status_from_min_threshold_returns_pass_when_observed_meets_threshold() -> None:
    assert _status_from_min_threshold(3, 1) == "pass"


def test_status_from_min_threshold_respects_custom_failing_status() -> None:
    assert _status_from_min_threshold(0, 1, failing_status="warn") == "warn"
