"""Small typed contracts for schedules, availability, and conflict alternatives."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class AvailableRoom(BaseModel):
    room_id: UUID
    name: str
    capacity: int


class OccupiedInterval(BaseModel):
    start_at: datetime
    end_at: datetime


class RoomScheduleResponse(BaseModel):
    room_id: UUID
    date: date
    timezone: str
    day_start: datetime
    day_end: datetime
    occupied: list[OccupiedInterval]


class AvailabilityResponse(BaseModel):
    start_at: datetime
    end_at: datetime
    rooms: list[AvailableRoom]


class AlternativeRoom(AvailableRoom):
    start_at: datetime
    end_at: datetime


class AlternativeSlot(BaseModel):
    room_id: UUID
    start_at: datetime
    end_at: datetime


class BookingConflictDetails(BaseModel):
    alternative_rooms: list[AlternativeRoom]
    alternative_slots: list[AlternativeSlot]
