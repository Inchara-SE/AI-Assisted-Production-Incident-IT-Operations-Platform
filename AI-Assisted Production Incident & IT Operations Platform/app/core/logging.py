"""Structured logging configuration using structlog with JSON output,
request-id binding and automatic secret redaction."""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

from app.core.config import get_settings

# Patterns considered secret — matched case-insensitively against event-dict keys.
_SECRET_KEY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"authorization", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
)

_REDACTED = "***REDACTED***"


def _redact_secrets(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Processor that replaces values whose keys look like secrets."""
    for key in list(event_dict.keys()):
        if any(pat.search(key) for pat in _SECRET_KEY_PATTERNS):
            event_dict[key] = _REDACTED
    return event_dict


def configure_logging() -> None:
    """Configure structlog for JSON logging with secret redaction.

    Call once during application startup.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.APP_LOG_LEVEL.upper(), logging.INFO)

    # Standard library root logger — captures third-party output.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            _redact_secrets,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger, optionally named."""
    return structlog.get_logger(name)
