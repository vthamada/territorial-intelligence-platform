from __future__ import annotations

from pathlib import Path

import psycopg
import yaml

from app.settings import get_settings


def load_connectors(path: Path) -> list[dict]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    connectors = payload.get("connectors", [])
    if not isinstance(connectors, list):
        return []
    return [item for item in connectors if isinstance(item, dict)]


def main() -> None:
    settings = get_settings()
    config_path = Path("configs/connectors.yml")
    if not config_path.exists():
        raise RuntimeError("Missing configs/connectors.yml")

    connectors = load_connectors(config_path)
    dsn = settings.database_url.replace("+psycopg", "")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for item in connectors:
                cur.execute(
                    """
                    INSERT INTO ops.connector_registry (
                        connector_name,
                        source,
                        wave,
                        status,
                        notes
                    ) VALUES (
                        %(connector_name)s,
                        %(source)s,
                        %(wave)s,
                        %(status)s,
                        %(notes)s
                    )
                    ON CONFLICT (connector_name) DO UPDATE SET
                        source = EXCLUDED.source,
                        wave = EXCLUDED.wave,
                        status = EXCLUDED.status,
                        notes = EXCLUDED.notes,
                        updated_at_utc = NOW()
                    """,
                    {
                        "connector_name": item.get("connector_name"),
                        "source": item.get("source"),
                        "wave": item.get("wave"),
                        "status": item.get("status"),
                        "notes": item.get("notes"),
                    },
                )
        conn.commit()

    print(f"Synchronized {len(connectors)} connectors into ops.connector_registry.")


if __name__ == "__main__":
    main()
