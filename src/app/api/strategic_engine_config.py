"""Strategic engine configuration loader.

Externalizes scoring thresholds, severity weights, and parameters
previously hardcoded in routes_qg.py.  Follows the same pattern as
pipelines.common.quality_thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ScoringConfig:
    critical_threshold: float = 80.0
    attention_threshold: float = 50.0
    severity_weights: dict[str, int] = field(default_factory=lambda: {"stable": 0, "attention": 1, "critical": 2})
    max_score: float = 100.0
    min_score: float = 0.0


@dataclass(frozen=True)
class StrategicEngineConfig:
    version: str = "1.0.0"
    scoring: ScoringConfig = field(default_factory=ScoringConfig)


@lru_cache(maxsize=1)
def load_strategic_engine_config(
    path: Path | str = "configs/strategic_engine.yml",
) -> StrategicEngineConfig:
    """Load strategic engine config from YAML (cached after first call)."""
    file_path = Path(path)
    if not file_path.exists():
        return StrategicEngineConfig()

    payload = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
    version = str(payload.get("version", "1.0.0"))

    scoring_raw = payload.get("scoring", {})
    scoring = ScoringConfig(
        critical_threshold=float(scoring_raw.get("critical_threshold", 80)),
        attention_threshold=float(scoring_raw.get("attention_threshold", 50)),
        severity_weights={
            k: int(v)
            for k, v in scoring_raw.get("severity_weights", {"stable": 0, "attention": 1, "critical": 2}).items()
        },
        max_score=float(scoring_raw.get("max_score", 100)),
        min_score=float(scoring_raw.get("min_score", 0)),
    )

    return StrategicEngineConfig(version=version, scoring=scoring)


def score_to_status(score: float, config: StrategicEngineConfig | None = None) -> str:
    """Convert a numeric score to a status label using config thresholds."""
    cfg = config or load_strategic_engine_config()
    if score >= cfg.scoring.critical_threshold:
        return "critical"
    if score >= cfg.scoring.attention_threshold:
        return "attention"
    return "stable"


def status_impact(before: str, after: str, config: StrategicEngineConfig | None = None) -> str:
    """Determine impact direction from status change."""
    cfg = config or load_strategic_engine_config()
    weights = cfg.scoring.severity_weights
    before_w = weights.get(before, 0)
    after_w = weights.get(after, 0)
    if after_w > before_w:
        return "worsened"
    if after_w < before_w:
        return "improved"
    return "unchanged"
