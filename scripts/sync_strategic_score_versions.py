from __future__ import annotations

import json
import sys
from pathlib import Path

import psycopg

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    src_str = str(SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

from app.api.strategic_engine_config import load_strategic_engine_config  # noqa: E402
from app.settings import get_settings  # noqa: E402


def main() -> int:
    settings = get_settings()
    cfg = load_strategic_engine_config()
    score_version = f"v{cfg.version}"

    params = {
        "score_version": score_version,
        "config_version": cfg.version,
        "status": "active",
        "scoring_method": "rank_abs_value_v1",
        "critical_threshold": cfg.scoring.critical_threshold,
        "attention_threshold": cfg.scoring.attention_threshold,
        "default_domain_weight": cfg.scoring.default_domain_weight,
        "default_indicator_weight": cfg.scoring.default_indicator_weight,
        "domain_weights": json.dumps(cfg.scoring.domain_weights, ensure_ascii=False),
        "indicator_weights": json.dumps(cfg.scoring.indicator_weights, ensure_ascii=False),
        "notes": "Synced from configs/strategic_engine.yml",
    }

    dsn = settings.database_url.replace("+psycopg", "")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ops.strategic_score_versions
                SET status = 'deprecated',
                    updated_at_utc = NOW()
                WHERE status = 'active'
                  AND score_version <> %(score_version)s
                """,
                params,
            )
            deprecated = int(cur.rowcount or 0)
            cur.execute(
                """
                INSERT INTO ops.strategic_score_versions (
                    score_version,
                    config_version,
                    status,
                    effective_from,
                    scoring_method,
                    critical_threshold,
                    attention_threshold,
                    default_domain_weight,
                    default_indicator_weight,
                    domain_weights,
                    indicator_weights,
                    notes
                ) VALUES (
                    %(score_version)s,
                    %(config_version)s,
                    %(status)s,
                    CURRENT_DATE,
                    %(scoring_method)s,
                    %(critical_threshold)s,
                    %(attention_threshold)s,
                    %(default_domain_weight)s,
                    %(default_indicator_weight)s,
                    CAST(%(domain_weights)s AS jsonb),
                    CAST(%(indicator_weights)s AS jsonb),
                    %(notes)s
                )
                ON CONFLICT (score_version) DO UPDATE SET
                    config_version = EXCLUDED.config_version,
                    status = EXCLUDED.status,
                    effective_from = EXCLUDED.effective_from,
                    scoring_method = EXCLUDED.scoring_method,
                    critical_threshold = EXCLUDED.critical_threshold,
                    attention_threshold = EXCLUDED.attention_threshold,
                    default_domain_weight = EXCLUDED.default_domain_weight,
                    default_indicator_weight = EXCLUDED.default_indicator_weight,
                    domain_weights = EXCLUDED.domain_weights,
                    indicator_weights = EXCLUDED.indicator_weights,
                    notes = EXCLUDED.notes,
                    updated_at_utc = NOW()
                """,
                params,
            )
            upserted = int(cur.rowcount or 0)
        conn.commit()

    print(
        "Synced strategic score version:"
        f" score_version={score_version}"
        f" config_version={cfg.version}"
        f" upserted={upserted}"
        f" deprecated={deprecated}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
