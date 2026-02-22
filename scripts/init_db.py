from __future__ import annotations

from pathlib import Path
from collections import defaultdict, deque

import psycopg

from app.settings import get_settings


def run_sql_file(conn: psycopg.Connection, sql_path: Path) -> None:
    content = sql_path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(content)


def sort_scripts_with_dependencies(scripts: list[Path]) -> list[Path]:
    """Topologically sort SQL scripts with explicit dependency overrides.

    Default order remains lexical; overrides are only used when both scripts exist.
    """
    by_name = {script.name: script for script in scripts}
    # db/sql/007_data_coverage_scorecard.sql references urban/environment objects from 009/010/012.
    dependency_overrides: dict[str, list[str]] = {
        "015_priority_drivers_mart.sql": [
            "016_strategic_score_versions.sql",
        ],
        "007_data_coverage_scorecard.sql": [
            "009_urban_domain.sql",
            "010_urban_transport_domain.sql",
            "012_environment_risk_aggregation.sql",
            "013_environment_risk_mart.sql",
            "014_source_schema_contracts.sql",
            "015_priority_drivers_mart.sql",
        ],
    }

    graph: dict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = {name: 0 for name in by_name}

    for target, deps in dependency_overrides.items():
        if target not in by_name:
            continue
        for dep in deps:
            if dep not in by_name:
                continue
            if target not in graph[dep]:
                graph[dep].add(target)
                indegree[target] += 1

    lexical_names = sorted(by_name)
    queue = deque(name for name in lexical_names if indegree[name] == 0)
    ordered_names: list[str] = []

    while queue:
        current = queue.popleft()
        ordered_names.append(current)
        for neighbor in sorted(graph.get(current, ())):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    # Fallback to lexical order if a cycle is ever introduced.
    if len(ordered_names) != len(by_name):
        ordered_names = lexical_names

    return [by_name[name] for name in ordered_names]


def main() -> None:
    settings = get_settings()
    dsn = settings.database_url.replace("+psycopg", "")
    sql_dir = Path("db/sql")
    scripts = sort_scripts_with_dependencies(sorted(sql_dir.glob("*.sql")))
    if not scripts:
        raise RuntimeError("No SQL scripts found in db/sql.")

    with psycopg.connect(dsn) as conn:
        for script in scripts:
            run_sql_file(conn, script)
        conn.commit()

    print(f"Applied {len(scripts)} SQL scripts.")


if __name__ == "__main__":
    main()
