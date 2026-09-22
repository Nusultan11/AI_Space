"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from typing import cast

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.types import ExceptionHandler

from app.api.health import router as health_router
from app.api.v1.router import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.errors import AppError, app_error_handler, request_validation_error_handler
from app.core.logging import configure_logging
from app.core.request_id import (
    REQUEST_ID_HEADER,
    choose_request_id,
    reset_request_id,
    set_request_id,
)
from app.db.session import check_database, create_database_engine, create_session_factory

logger = structlog.get_logger(__name__)


def create_app(settings: Settings | None = None, engine: AsyncEngine | None = None) -> FastAPI:
    effective_settings = settings or get_settings()
    configure_logging(effective_settings.app_log_level)
    database_engine = engine or create_database_engine(effective_settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        await database_engine.dispose()

    application = FastAPI(title="AiSpace API", version="0.1.0", lifespan=lifespan)
    application.state.settings = effective_settings
    application.state.database_engine = database_engine
    application.state.session_factory = create_session_factory(database_engine)
    application.state.database_healthcheck = partial(check_database, database_engine)
    application.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(
        RequestValidationError,
        cast(ExceptionHandler, request_validation_error_handler),
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        request_id = choose_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        token = set_request_id(request_id)
        try:
            logger.info("request_started", method=request.method, path=request.url.path)
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
            )
            return response
        finally:
            reset_request_id(token)

    application.include_router(health_router, prefix="/api/v1")
    application.include_router(api_v1_router, prefix="/api/v1")
    return application


app = create_app()
