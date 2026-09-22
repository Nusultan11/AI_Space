"""Request identifier validation, propagation, and logging context."""

from __future__ import annotations

import re
from contextvars import ContextVar, Token
from uuid import uuid4

from structlog.contextvars import bind_contextvars, clear_contextvars

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def choose_request_id(candidate: str | None) -> str:
    if candidate is not None and REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return str(uuid4())


def set_request_id(value: str) -> Token[str | None]:
    clear_contextvars()
    bind_contextvars(request_id=value)
    return _request_id.set(value)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)
    clear_contextvars()


def get_request_id() -> str | None:
    return _request_id.get()
