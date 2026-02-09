from __future__ import annotations

from pipelines.tse_catalog import _summarize


def test_summarize_extracts_package_metadata() -> None:
    payload = {
        "result": {
            "results": [
                {
                    "id": "abc",
                    "name": "eleitorado-2024",
                    "title": "Eleitorado - 2024",
                    "resources": [{"id": "r1"}, {"id": "r2"}],
                }
            ]
        }
    }
    items = _summarize(payload)
    assert len(items) == 1
    assert items[0]["id"] == "abc"
    assert items[0]["resources_count"] == 2
