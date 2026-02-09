from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class QualityThresholds:
    defaults: dict[str, float]
    by_table: dict[str, dict[str, float]]

    def get(self, table: str, key: str, fallback: float = 0.0) -> float:
        if table in self.by_table and key in self.by_table[table]:
            return float(self.by_table[table][key])
        if key in self.defaults:
            return float(self.defaults[key])
        return fallback


def load_quality_thresholds(path: Path | str = "configs/quality_thresholds.yml") -> QualityThresholds:
    file_path = Path(path)
    if not file_path.exists():
        return QualityThresholds(defaults={}, by_table={})

    payload = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
    defaults = payload.get("defaults", {})
    by_table: dict[str, dict[str, float]] = {}
    for key, value in payload.items():
        if key == "defaults":
            continue
        if isinstance(value, dict):
            by_table[key] = {k: float(v) for k, v in value.items()}
    return QualityThresholds(
        defaults={k: float(v) for k, v in defaults.items()},
        by_table=by_table,
    )


def as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
