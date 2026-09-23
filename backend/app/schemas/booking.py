"""Booking request and response contracts."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from app.models.booking import BookingStatus

BookingTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class BookingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: UUID
    title: BookingTitle
    start_at: AwareDatetime
    end_at: AwareDatetime
    participants_count: int | None = Field(default=None, ge=1)


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    room_id: UUID
    user_id: UUID
    title: str
    start_at: datetime
    end_at: datetime
    status: BookingStatus
    participants_count: int | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
