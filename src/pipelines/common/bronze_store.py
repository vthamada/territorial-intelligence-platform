from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.settings import Settings
from pipelines.common.manifest import build_manifest, write_manifest


@dataclass(frozen=True)
class BronzeArtifact:
    source: str
    dataset: str
    reference_period: str
    extracted_at_utc: str
    local_path: Path
    manifest_path: Path
    size_bytes: int
    checksum_sha256: str
    uri: str


def sha256_file(path: Path) -> str:
    hasher = sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _slug(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def _timestamp_folder(extracted_at: datetime) -> str:
    return extracted_at.replace(microsecond=0).isoformat().replace("+00:00", "Z").replace(":", "-")


def persist_raw_bytes(
    *,
    settings: Settings,
    source: str,
    dataset: str,
    reference_period: str,
    raw_bytes: bytes,
    extension: str,
    uri: str,
    territory_scope: str,
    dataset_version: str = "unknown",
    checks: list[dict[str, str]] | None = None,
    notes: str = "",
    extracted_at: datetime | None = None,
    run_id: str | None = None,
    tables_written: list[str] | None = None,
    rows_written: list[dict[str, int]] | None = None,
) -> BronzeArtifact:
    extracted_at = extracted_at or datetime.now(UTC)
    if extracted_at.tzinfo is None:
        extracted_at = extracted_at.replace(tzinfo=UTC)
    extracted_at_utc = extracted_at.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    source_slug = _slug(source)
    dataset_slug = _slug(dataset)
    period_slug = _slug(reference_period)
    ts_folder = _timestamp_folder(extracted_at)
    safe_extension = extension if extension.startswith(".") else f".{extension}"

    bronze_dir = (
        settings.bronze_root / source_slug / dataset_slug / period_slug / f"extracted_at={ts_folder}"
    )
    bronze_dir.mkdir(parents=True, exist_ok=True)
    raw_path = bronze_dir / f"raw{safe_extension}"
    raw_path.write_bytes(raw_bytes)

    checksum = sha256_file(raw_path)
    size_bytes = raw_path.stat().st_size

    manifest_path = (
        settings.manifests_root
        / source_slug
        / dataset_slug
        / period_slug
        / f"extracted_at={ts_folder}.yml"
    )

    manifest = build_manifest(
        settings=settings,
        source=source,
        dataset=dataset,
        dataset_version=dataset_version,
        territory_scope=territory_scope,
        reference_period=reference_period,
        raw_format=safe_extension.removeprefix("."),
        raw_uri=uri,
        raw_local_path=raw_path.as_posix(),
        raw_size_bytes=size_bytes,
        raw_checksum_sha256=checksum,
        checks=checks,
        notes=notes,
        extracted_at_utc=extracted_at_utc,
        run_id=run_id,
        tables_written=tables_written,
        rows_written=rows_written,
    )
    write_manifest(manifest, manifest_path)

    return BronzeArtifact(
        source=source,
        dataset=dataset,
        reference_period=reference_period,
        extracted_at_utc=extracted_at_utc,
        local_path=raw_path,
        manifest_path=manifest_path,
        size_bytes=size_bytes,
        checksum_sha256=checksum,
        uri=uri,
    )


def artifact_to_dict(artifact: BronzeArtifact) -> dict[str, Any]:
    return {
        "source": artifact.source,
        "dataset": artifact.dataset,
        "reference_period": artifact.reference_period,
        "extracted_at_utc": artifact.extracted_at_utc,
        "local_path": artifact.local_path.as_posix(),
        "manifest_path": artifact.manifest_path.as_posix(),
        "size_bytes": artifact.size_bytes,
        "checksum_sha256": artifact.checksum_sha256,
        "uri": artifact.uri,
    }
