from __future__ import annotations

from typing import Any

from scripts import validate_mte_p0


def test_main_returns_zero_when_all_runs_are_success(monkeypatch, capsys) -> None:
    calls: dict[str, int] = {"mte": 0, "ibge": 0}

    def _run_mte(**_kwargs: Any) -> dict[str, Any]:
        calls["mte"] += 1
        return {
            "status": "success",
            "rows_extracted": 10,
            "rows_written": 4,
            "warnings": [],
            "errors": [],
            "run_id": f"run-{calls['mte']}",
        }

    def _run_ibge(**_kwargs: Any) -> dict[str, Any]:
        calls["ibge"] += 1
        return {"status": "success"}

    monkeypatch.setattr(validate_mte_p0, "run_mte_labor", _run_mte)
    monkeypatch.setattr(validate_mte_p0, "run_ibge_admin", _run_ibge)

    exit_code = validate_mte_p0.main(
        ["--reference-period", "2025", "--runs", "3", "--bootstrap-municipality", "--output-json"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert calls["ibge"] == 1
    assert calls["mte"] == 3
    assert "MTE P0 validation: 3/3 successful runs." in captured.out
    assert "\"all_successful\": true" in captured.out


def test_main_returns_one_when_any_run_fails(monkeypatch, capsys) -> None:
    statuses = iter(["success", "blocked", "success"])

    def _run_mte(**_kwargs: Any) -> dict[str, Any]:
        status = next(statuses)
        return {
            "status": status,
            "rows_extracted": 0,
            "rows_written": 0,
            "warnings": [],
            "errors": [],
            "run_id": "run-x",
        }

    monkeypatch.setattr(validate_mte_p0, "run_mte_labor", _run_mte)
    monkeypatch.setattr(validate_mte_p0, "run_ibge_admin", lambda **_kwargs: {"status": "success"})

    exit_code = validate_mte_p0.main(["--reference-period", "2025", "--runs", "3"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "MTE P0 validation: 2/3 successful runs." in captured.out
