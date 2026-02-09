from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.settings import Settings
from pipelines.common.bronze_store import persist_raw_bytes


def test_persist_raw_bytes_creates_raw_and_manifest() -> None:
    tmp_path = Path("tests/_tmp") / str(uuid4())
    tmp_path.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        data_root=tmp_path,
        database_url="postgresql+psycopg://postgres:postgres@localhost:5432/test",
    )
    artifact = persist_raw_bytes(
        settings=settings,
        source="IBGE",
        dataset="localidades",
        reference_period="2026",
        raw_bytes=b'{"ok": true}',
        extension=".json",
        uri="https://example.com/file.json",
        territory_scope="distrito",
    )

    assert artifact.local_path.exists()
    assert artifact.local_path.read_bytes() == b'{"ok": true}'
    assert artifact.manifest_path.exists()
    assert artifact.size_bytes > 0
    assert len(artifact.checksum_sha256) == 64
