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
Interpret relative dates and requested wall-clock times in the supplied office
timezone, using current_local_datetime as the reference. Return start_at and
end_at as those office-local wall-clock values with the correct UTC offset for
each date; do not return UTC-converted wall-clock values. If the date or time is
ambiguous, ask for clarification. Do not check or claim room availability.
Do not create a booking. Missing or ambiguous critical values must set
needs_clarification=true, list the missing fields, and include a concise question.
Example JSON for a request that needs clarification:
{
  "room_id": null,
  "room_reference": null,
  "start_at": null,
  "end_at": null,
  "title": null,
  "participants_count": null,
  "needs_clarification": true,
  "missing_fields": ["room_id", "start_at", "end_at", "title"],
  "clarification_message": "Which room, time, and title should I use?"
}
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
