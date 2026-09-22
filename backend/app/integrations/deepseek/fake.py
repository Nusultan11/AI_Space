"""Deterministic parser fake for service and API tests."""

from __future__ import annotations

from datetime import datetime

from app.schemas.ai_booking import BookingIntent, RoomContext


class FakeBookingIntentParser:
    def __init__(self, result: BookingIntent | Exception) -> None:
        self.result = result

    async def parse(
        self,
        *,
        text: str,
        current_local_datetime: datetime,
        timezone: str,
        rooms: list[RoomContext],
    ) -> BookingIntent:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result.model_copy(deep=True)
