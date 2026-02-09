from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from app.settings import Settings

_REQUIRED_TOP_LEVEL = {
    "source",
    "dataset",
    "territory_ibge_code",
    "territory_scope",
    "reference_period",
    "extracted_at_utc",
    "raw",
    "ingestion",
    "validation",
    "load",
}
_REQUIRED_RAW = {"format", "uri", "local_path", "size_bytes", "checksum_sha256"}


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_manifest(
    *,
    settings: Settings,
    source: str,
    dataset: str,
    dataset_version: str,
    territory_scope: str,
    reference_period: str,
    raw_format: str,
    raw_uri: str,
    raw_local_path: str,
    raw_size_bytes: int,
    raw_checksum_sha256: str,
    tables_written: list[str] | None = None,
    rows_written: list[dict[str, int]] | None = None,
    checks: list[dict[str, str]] | None = None,
    notes: str = "",
    extracted_at_utc: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "dataset": dataset,
        "dataset_version": dataset_version,
        "territory_ibge_code": settings.municipality_ibge_code,
        "territory_scope": territory_scope,
        "reference_period": reference_period,
        "extracted_at_utc": extracted_at_utc or utc_now_iso(),
        "raw": {
            "format": raw_format,
            "uri": raw_uri,
            "local_path": raw_local_path,
            "size_bytes": raw_size_bytes,
            "checksum_sha256": raw_checksum_sha256,
        },
        "ingestion": {
            "tool": "python",
            "orchestrator": settings.orchestrator_name,
            "pipeline_version": settings.pipeline_version,
            "run_id": run_id or str(uuid4()),
        },
        "validation": {
            "schema_version": "1.0.0",
            "checks": checks or [],
        },
        "load": {
            "destination": settings.database_url,
            "tables_written": tables_written or [],
            "rows_written": rows_written or [],
        },
        "notes": notes,
    }


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = _REQUIRED_TOP_LEVEL - set(manifest.keys())
    if missing:
        errors.append(f"Missing top-level keys: {sorted(missing)}")

    raw_section = manifest.get("raw", {})
    if isinstance(raw_section, dict):
        raw_missing = _REQUIRED_RAW - set(raw_section.keys())
        if raw_missing:
            errors.append(f"Missing raw keys: {sorted(raw_missing)}")
    else:
        errors.append("Field 'raw' must be a mapping.")

    return errors


def write_manifest(manifest: dict[str, Any], path: Path) -> None:
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError("; ".join(errors))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")
