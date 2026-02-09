from __future__ import annotations

from fastapi import HTTPException

from app.api.territory_levels import normalize_level, to_external_level


def test_normalize_level_accepts_pt_and_en() -> None:
    assert normalize_level("municipio") == "municipality"
    assert normalize_level("district") == "district"


def test_normalize_level_raises_for_invalid_value() -> None:
    try:
        normalize_level("bairro")
        assert False, "Expected HTTPException for invalid level."
    except HTTPException as exc:
        assert exc.status_code == 422


def test_to_external_level_maps_to_portuguese() -> None:
    assert to_external_level("municipality") == "municipio"
