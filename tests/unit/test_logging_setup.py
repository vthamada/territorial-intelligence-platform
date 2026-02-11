from __future__ import annotations

import structlog

from app.logging import get_logger


def test_get_logger_configures_structlog_when_needed() -> None:
    structlog.reset_defaults()
    assert not structlog.is_configured()

    logger = get_logger("unit-test-logger")

    assert structlog.is_configured()
    logger.info("logging_setup_probe")
