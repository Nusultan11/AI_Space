"""DeepSeek structured-output parser with safe provider error translation."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Protocol, cast

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from pydantic import ValidationError

from app.core.errors import AppError
from app.integrations.deepseek.prompt import build_messages
from app.schemas.ai_booking import BookingIntent, RoomContext


class BookingIntentParser(Protocol):
    async def parse(
        self,
        *,
        text: str,
        current_local_datetime: datetime,
        timezone: str,
        rooms: list[RoomContext],
    ) -> BookingIntent: ...


class CompletionClient(Protocol):
    async def create(self, **kwargs: Any) -> Any: ...


class DeepSeekBookingIntentParser:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout_seconds: float,
        completion_client: CompletionClient | None = None,
    ) -> None:
        self.model = model
        if completion_client is not None:
            self.completions = completion_client
        elif api_key is not None and api_key.strip():
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout_seconds,
                max_retries=0,
            )
            self.completions = cast(CompletionClient, client.chat.completions)
        else:
            self.completions = None

    async def parse(
        self,
        *,
        text: str,
        current_local_datetime: datetime,
        timezone: str,
        rooms: list[RoomContext],
    ) -> BookingIntent:
        if self.completions is None:
            raise ai_unavailable()
        try:
            response = await self.completions.create(
                model=self.model,
                messages=build_messages(
                    text=text,
                    current_local_datetime=current_local_datetime,
                    timezone=timezone,
                    rooms=rooms,
                ),
                response_format={"type": "json_object"},
                temperature=0,
            )
        except APITimeoutError:
            raise ai_timeout() from None
        except (RateLimitError, APIStatusError, APIConnectionError, APIError):
            raise ai_unavailable() from None

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError):
            raise ai_invalid_response() from None
        if not isinstance(content, str) or not content.strip():
            raise ai_invalid_response()
        try:
            decoded = json.loads(content)
            return BookingIntent.model_validate(decoded)
        except (json.JSONDecodeError, ValidationError, TypeError):
            raise ai_invalid_response() from None


def ai_timeout() -> AppError:
    return AppError(
        status_code=504,
        code="ai_timeout",
        message="AI booking assistance timed out.",
    )


def ai_unavailable() -> AppError:
    return AppError(
        status_code=503,
        code="ai_unavailable",
        message="AI booking assistance is temporarily unavailable.",
    )


def ai_invalid_response() -> AppError:
    return AppError(
        status_code=502,
        code="ai_invalid_response",
        message="AI booking assistance returned an invalid preview.",
    )
