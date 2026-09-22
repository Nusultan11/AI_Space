"""Structured logging configuration and conservative secret redaction."""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping
from typing import Any

import structlog
from structlog.typing import EventDict, WrappedLogger

REDACTED = "[REDACTED]"
SENSITIVE_KEY_PARTS = {
    "api_key",
    "authorization",
    "jwt",
    "password",
    "password_hash",
    "secret",
    "token",
}
PRIVATE_CONTENT_KEYS = {"meeting_content", "meeting_description", "private_content"}


def _normalized_key(key: object) -> str:
    return str(key).casefold().replace("-", "_")


def _is_sensitive_key(key: object) -> bool:
    normalized = _normalized_key(key)
    return normalized in PRIVATE_CONTENT_KEYS or any(
        part in normalized for part in SENSITIVE_KEY_PARTS
    )


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): REDACTED if _is_sensitive_key(key) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    return value


def redact_sensitive(
    _logger: WrappedLogger,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Redact sensitive values recursively before rendering a log event."""

    return _redact(event_dict)


def configure_logging(level: str = "INFO") -> None:
    """Configure stdlib and structlog to emit one JSON object per line."""

    logging.basicConfig(stream=sys.stdout, level=level, format="%(message)s", force=True)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_sensitive,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
