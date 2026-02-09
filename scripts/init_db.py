from __future__ import annotations

from pathlib import Path

import psycopg

from app.settings import get_settings


def run_sql_file(conn: psycopg.Connection, sql_path: Path) -> None:
    content = sql_path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(content)


def main() -> None:
    settings = get_settings()
    dsn = settings.database_url.replace("+psycopg", "")
    sql_dir = Path("db/sql")
    scripts = sorted(sql_dir.glob("*.sql"))
    if not scripts:
        raise RuntimeError("No SQL scripts found in db/sql.")

    with psycopg.connect(dsn) as conn:
        for script in scripts:
            run_sql_file(conn, script)
        conn.commit()

    print(f"Applied {len(scripts)} SQL scripts.")


if __name__ == "__main__":
    main()
