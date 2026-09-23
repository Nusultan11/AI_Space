"""Contracts for natural-language booking intent previews."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

UserBookingText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]


class AIBookingIntentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: UserBookingText


class RoomContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    capacity: int


class BookingIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: UUID | None = None
    room_reference: str | None = None
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    title: Annotated[str, StringConstraints(max_length=200)] | None = None
    participants_count: int | None = Field(default=None, ge=1)
    needs_clarification: bool
    missing_fields: list[str] = Field(default_factory=list)
    clarification_message: str | None = None


class ParserContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_local_datetime: datetime
    timezone: str
    rooms: list[RoomContext]
