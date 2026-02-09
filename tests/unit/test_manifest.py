from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.settings import Settings
from pipelines.common.manifest import build_manifest, validate_manifest, write_manifest


def _local_test_dir() -> Path:
    path = Path("tests/_tmp") / str(uuid4())
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_manifest_build_and_validate() -> None:
    tmp_path = _local_test_dir()
    settings = Settings(data_root=tmp_path, database_url="postgresql+psycopg://x:y@localhost:5432/test")
    manifest = build_manifest(
        settings=settings,
        source="IBGE",
        dataset="localidades",
        dataset_version="api-v1",
        territory_scope="distrito",
        reference_period="2026",
        raw_format="json",
        raw_uri="https://example.com/file.json",
        raw_local_path="data/bronze/ibge/file.json",
        raw_size_bytes=10,
        raw_checksum_sha256="abc",
    )

    errors = validate_manifest(manifest)
    assert errors == []


def test_manifest_write_fails_when_missing_required_keys() -> None:
    tmp_path = _local_test_dir()
    bad_manifest = {"source": "IBGE"}
    target = tmp_path / "manifest.yml"
    try:
        write_manifest(bad_manifest, target)
        assert False, "Expected ValueError for invalid manifest"
    except ValueError:
        assert not target.exists()
