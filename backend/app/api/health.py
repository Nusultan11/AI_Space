"""Process liveness and PostgreSQL readiness endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import AppError, ErrorEnvelope

router = APIRouter(prefix="/health", tags=["health"])
logger = structlog.get_logger(__name__)


class HealthResponse(BaseModel):
    status: str


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    """Report process liveness without touching external dependencies."""

    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={503: {"model": ErrorEnvelope}},
)
async def ready(request: Request) -> HealthResponse:
    """Report readiness after a minimal PostgreSQL query."""

    healthcheck = cast(Callable[[], Awaitable[None]], request.app.state.database_healthcheck)
    try:
        await healthcheck()
    except (OSError, SQLAlchemyError):
        logger.warning("database_readiness_failed")
        raise AppError(
            status_code=503,
            code="database_unavailable",
            message="Database is unavailable.",
        ) from None
    return HealthResponse(status="ready")
