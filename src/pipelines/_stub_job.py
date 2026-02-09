from __future__ import annotations

from typing import Any

from app.logging import get_logger


def not_implemented_result(job_name: str, reference_period: str, dry_run: bool) -> dict[str, Any]:
    logger = get_logger(job_name)
    logger.warning("Job is scaffolded but not implemented yet.", reference_period=reference_period)
    return {
        "job": job_name,
        "status": "not_implemented",
        "reference_period": reference_period,
        "dry_run": dry_run,
        "rows_extracted": 0,
        "rows_written": 0,
        "warnings": ["Job scaffolded; implementation pending."],
        "errors": [],
    }
