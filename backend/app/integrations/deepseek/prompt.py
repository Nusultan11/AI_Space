"""Narrow prompt construction for booking-intent extraction."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TypedDict

from app.schemas.ai_booking import RoomContext

SYSTEM_PROMPT = """You extract a meeting-room booking intent and return JSON only.
Use exactly these keys: room_id, room_reference, start_at, end_at, title,
participants_count, needs_clarification, missing_fields, clarification_message.
Never invent a room, date, time, duration, or title. Expressions such as
"after lunch" are ambiguous and require clarification. room_id must be null or
one ID from the supplied active-room catalog. participants_count is optional.
Timestamps must include a UTC offset. Do not check or claim room availability.
Do not create a booking. Missing or ambiguous critical values must set
needs_clarification=true, list the missing fields, and include a concise question.
"""


class PromptMessage(TypedDict):
    role: str
    content: str


def build_messages(
    *,
    text: str,
    current_local_datetime: datetime,
    timezone: str,
    rooms: list[RoomContext],
) -> list[PromptMessage]:
    context = {
        "user_text": text,
        "current_local_datetime": current_local_datetime.isoformat(),
        "timezone": timezone,
        "active_rooms": [room.model_dump(mode="json") for room in rooms],
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
    ]
