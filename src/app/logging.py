from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: str = "INFO") -> None:
    logging_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=logging_level, format="%(message)s", stream=sys.stdout)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging_level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    return structlog.get_logger(name)
