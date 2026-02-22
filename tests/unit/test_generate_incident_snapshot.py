from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    module_path = Path("scripts/generate_incident_snapshot.py")
    spec = importlib.util.spec_from_file_location("generate_incident_snapshot", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_classify_incident_returns_critical_on_hard_failure() -> None:
    module = _load_module()

    severity = module._classify_incident(
        hard_failures=1,
        warnings=0,
        failed_runs=0,
        failed_checks=0,
    )

    assert severity == "critical"


def test_classify_incident_returns_high_on_warnings_only() -> None:
    module = _load_module()

    severity = module._classify_incident(
        hard_failures=0,
        warnings=2,
        failed_runs=0,
        failed_checks=0,
    )

    assert severity == "high"


def test_recommended_actions_has_default_when_normal() -> None:
    module = _load_module()

    actions = module._recommended_actions(
        "normal",
        hard_failures=0,
        failed_runs=0,
        failed_checks=0,
    )

    assert len(actions) == 1
    assert "sem acao corretiva imediata" in actions[0]
