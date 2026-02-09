from __future__ import annotations

from fastapi import HTTPException

PT_TO_EN = {
    "municipio": "municipality",
    "distrito": "district",
    "setor_censitario": "census_sector",
    "zona_eleitoral": "electoral_zone",
    "secao_eleitoral": "electoral_section",
}
EN_TO_PT = {value: key for key, value in PT_TO_EN.items()}
ALL_LEVELS_EN = set(EN_TO_PT.keys())
ALL_LEVELS_PT = set(PT_TO_EN.keys())


def normalize_level(level: str | None) -> str | None:
    if level is None:
        return None
    value = level.strip().lower()
    if value in ALL_LEVELS_EN:
        return value
    if value in PT_TO_EN:
        return PT_TO_EN[value]
    raise HTTPException(
        status_code=422,
        detail=f"Invalid level '{level}'. Expected one of {sorted(ALL_LEVELS_EN | ALL_LEVELS_PT)}.",
    )


def to_external_level(level_en: str) -> str:
    return EN_TO_PT.get(level_en, level_en)
