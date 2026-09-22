"""Preview-only orchestration and independent BookingIntent validation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.deepseek.parser import BookingIntentParser, ai_invalid_response
from app.repositories.rooms import RoomsRepository
from app.schemas.ai_booking import BookingIntent, RoomContext

CRITICAL_FIELDS = ("room_id", "start_at", "end_at", "title")
FIELD_LABELS = {
    "room_id": "room",
    "start_at": "start time",
    "end_at": "end time or duration",
    "title": "title",
}


class AIBookingService:
    def __init__(
        self,
        session: AsyncSession,
        parser: BookingIntentParser,
        *,
        office_timezone: str,
        clock: Callable[[ZoneInfo], datetime] | None = None,
    ) -> None:
        self.rooms = RoomsRepository(session)
        self.parser = parser
        self.office_timezone = office_timezone
        self.clock = clock or (lambda timezone: datetime.now(timezone))

    async def preview(self, *, text: str) -> BookingIntent:
        rooms = [
            RoomContext(id=room.id, name=room.name, capacity=room.capacity)
            for room in await self.rooms.list_active()
        ]
        current_local_datetime = self.clock(ZoneInfo(self.office_timezone))
        intent = await self.parser.parse(
            text=text,
            current_local_datetime=current_local_datetime,
            timezone=self.office_timezone,
            rooms=rooms,
        )
        return validate_booking_intent(
            intent,
            rooms=rooms,
            current_local_datetime=current_local_datetime,
        )


def validate_booking_intent(
    intent: BookingIntent,
    *,
    rooms: list[RoomContext],
    current_local_datetime: datetime,
) -> BookingIntent:
    rooms_by_id = {room.id: room for room in rooms}
    if intent.room_id is not None and intent.room_id not in rooms_by_id:
        raise ai_invalid_response()

    start_at = intent.start_at
    end_at = intent.end_at
    if start_at is not None and not is_timezone_aware(start_at):
        raise ai_invalid_response()
    if end_at is not None and not is_timezone_aware(end_at):
        raise ai_invalid_response()
    if start_at is not None and start_at < current_local_datetime:
        raise ai_invalid_response()
    if start_at is not None and end_at is not None and end_at <= start_at:
        raise ai_invalid_response()
    if intent.participants_count is not None and intent.participants_count < 1:
        raise ai_invalid_response()
    if (
        intent.room_id is not None
        and intent.participants_count is not None
        and intent.participants_count > rooms_by_id[intent.room_id].capacity
    ):
        raise ai_invalid_response()

    title = intent.title.strip() if intent.title is not None else None
    if not title:
        title = None
    missing = list(
        dict.fromkeys(field for field in intent.missing_fields if field in CRITICAL_FIELDS)
    )
    values = {
        "room_id": intent.room_id,
        "start_at": start_at,
        "end_at": end_at,
        "title": title,
    }
    for field in CRITICAL_FIELDS:
        if values[field] is None and field not in missing:
            missing.append(field)

    needs_clarification = intent.needs_clarification or bool(missing)
    if needs_clarification:
        message = normalized_clarification_message(intent.clarification_message, missing)
        return intent.model_copy(
            update={
                "title": title,
                "needs_clarification": True,
                "missing_fields": missing,
                "clarification_message": message,
            }
        )
    return intent.model_copy(
        update={
            "title": title,
            "missing_fields": [],
            "clarification_message": None,
        }
    )


def normalized_clarification_message(message: str | None, missing: list[str]) -> str:
    if message is not None and message.strip():
        return message.strip()
    if missing:
        labels = ", ".join(FIELD_LABELS[field] for field in missing)
        return f"Please provide: {labels}."
    return "Please clarify the booking details."


def is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
