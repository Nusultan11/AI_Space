"""Small shared API error contract."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    envelope = ErrorEnvelope(
        error=ErrorBody(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request_id,
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope.model_dump(mode="json", exclude_none=True),
    )


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return safe validation metadata without echoing submitted values."""

    safe_errors = [
        {
            "location": [str(part) for part in error.get("loc", ())],
            "message": str(error.get("msg", "Invalid value.")),
            "type": str(error.get("type", "validation_error")),
        }
        for error in exc.errors()
    ]
    envelope = ErrorEnvelope(
        error=ErrorBody(
            code="validation_error",
            message="The request contains invalid values.",
            details={"errors": safe_errors},
            request_id=getattr(request.state, "request_id", "unknown"),
        )
    )
    return JSONResponse(
        status_code=422,
        content=envelope.model_dump(mode="json", exclude_none=True),
    )
