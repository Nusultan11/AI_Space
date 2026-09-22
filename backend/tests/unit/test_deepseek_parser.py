from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from openai import APITimeoutError, InternalServerError, RateLimitError

from app.core.errors import AppError
from app.integrations.deepseek.parser import DeepSeekBookingIntentParser
from app.schemas.ai_booking import RoomContext


class StubCompletions:
    def __init__(self, *, content: str | None = None, error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.request: dict | None = None

    async def create(self, **kwargs):
        self.request = kwargs
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


def _parser(completions: StubCompletions) -> DeepSeekBookingIntentParser:
    return DeepSeekBookingIntentParser(
        api_key=None,
        base_url="https://provider.invalid",
        model="test-model",
        timeout_seconds=1,
        completion_client=completions,
    )


def _context() -> tuple[RoomContext, datetime]:
    return RoomContext(id=uuid4(), name="Room A", capacity=4), datetime(
        2030, 1, 1, 9, 0, tzinfo=UTC
    )


async def _parse(completions: StubCompletions):
    room, now = _context()
    intent = await _parser(completions).parse(
        text="Book Room A tomorrow at 10 for planning",
        current_local_datetime=now,
        timezone="Asia/Almaty",
        rooms=[room],
    )
    return intent, room, now


@pytest.mark.asyncio
async def test_parser_accepts_valid_json_and_sends_only_narrow_context() -> None:
    room, now = _context()
    content = json.dumps(
        {
            "room_id": str(room.id),
            "room_reference": "Room A",
            "start_at": (now + timedelta(days=1)).isoformat(),
            "end_at": (now + timedelta(days=1, hours=1)).isoformat(),
            "title": "Planning",
            "participants_count": 3,
            "needs_clarification": False,
            "missing_fields": [],
            "clarification_message": None,
        }
    )
    completions = StubCompletions(content=content)
    intent = await _parser(completions).parse(
        text="Book Room A tomorrow at 10 for planning",
        current_local_datetime=now,
        timezone="Asia/Almaty",
        rooms=[room],
    )

    assert intent.room_id == room.id
    assert intent.needs_clarification is False
    assert completions.request is not None
    assert completions.request["response_format"] == {"type": "json_object"}
    provider_context = json.loads(completions.request["messages"][1]["content"])
    assert set(provider_context) == {
        "user_text",
        "current_local_datetime",
        "timezone",
        "active_rooms",
    }
    assert provider_context["active_rooms"] == [
        {"id": str(room.id), "name": "Room A", "capacity": 4}
    ]


@pytest.mark.asyncio
async def test_parser_accepts_clarification_json() -> None:
    completions = StubCompletions(
        content=json.dumps(
            {
                "room_id": None,
                "room_reference": None,
                "start_at": None,
                "end_at": None,
                "title": None,
                "participants_count": None,
                "needs_clarification": True,
                "missing_fields": ["room_id", "start_at", "end_at", "title"],
                "clarification_message": "Which room and time should I use?",
            }
        )
    )

    intent, _, _ = await _parse(completions)

    assert intent.needs_clarification is True
    assert intent.room_id is None


@pytest.mark.parametrize(
    "content",
    [
        None,
        "   ",
        "not-json",
        json.dumps({"needs_clarification": False, "unexpected": True}),
        json.dumps({"needs_clarification": "not-a-boolean"}),
    ],
)
@pytest.mark.asyncio
async def test_parser_rejects_empty_invalid_and_schema_invalid_output(content: str | None) -> None:
    with pytest.raises(AppError) as error:
        await _parse(StubCompletions(content=content))

    assert error.value.status_code == 502
    assert error.value.code == "ai_invalid_response"


@pytest.mark.parametrize(
    ("provider_error", "status_code", "code"),
    [
        (
            APITimeoutError(request=httpx.Request("POST", "https://provider.invalid")),
            504,
            "ai_timeout",
        ),
        (
            RateLimitError(
                "rate limited",
                response=httpx.Response(
                    429,
                    request=httpx.Request("POST", "https://provider.invalid"),
                ),
                body=None,
            ),
            503,
            "ai_unavailable",
        ),
        (
            InternalServerError(
                "provider failed",
                response=httpx.Response(
                    500,
                    request=httpx.Request("POST", "https://provider.invalid"),
                ),
                body=None,
            ),
            503,
            "ai_unavailable",
        ),
    ],
)
@pytest.mark.asyncio
async def test_parser_maps_provider_failures(
    provider_error: Exception,
    status_code: int,
    code: str,
) -> None:
    with pytest.raises(AppError) as error:
        await _parse(StubCompletions(error=provider_error))

    assert error.value.status_code == status_code
    assert error.value.code == code


@pytest.mark.asyncio
async def test_parser_without_api_key_is_unavailable() -> None:
    room, now = _context()
    parser = DeepSeekBookingIntentParser(
        api_key=" ",
        base_url="https://provider.invalid",
        model="test-model",
        timeout_seconds=1,
    )

    with pytest.raises(AppError) as error:
        await parser.parse(
            text="Book a room",
            current_local_datetime=now,
            timezone="Asia/Almaty",
            rooms=[room],
        )

    assert error.value.status_code == 503
    assert error.value.code == "ai_unavailable"
