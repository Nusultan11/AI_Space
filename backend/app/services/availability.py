"""Deterministic schedule, free-room, and alternative calculations."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.room import Room
from app.repositories.bookings import BookingsRepository
from app.repositories.rooms import RoomsRepository
from app.schemas.availability import (
    AlternativeRoom,
    AlternativeSlot,
    AvailabilityResponse,
    AvailableRoom,
    BookingConflictDetails,
    OccupiedInterval,
    RoomScheduleResponse,
)

SLOT_GRANULARITY = timedelta(minutes=15)
SLOT_SEARCH_HORIZON = timedelta(days=7)
ALTERNATIVE_LIMIT = 3


class AvailabilityService:
    def __init__(self, session: AsyncSession, *, office_timezone: str = "Asia/Almaty") -> None:
        self.bookings = BookingsRepository(session)
        self.rooms = RoomsRepository(session)
        self.office_timezone = office_timezone

    async def room_schedule(self, *, room_id: UUID, local_date: date) -> RoomScheduleResponse:
        room = await self.rooms.get_active_by_id(room_id)
        if room is None:
            raise room_not_found()
        day_start, day_end = local_day_bounds(local_date, self.office_timezone)
        bookings = await self.bookings.list_confirmed_overlapping(
            room_id=room.id,
            start_at=day_start,
            end_at=day_end,
        )
        return RoomScheduleResponse(
            room_id=room.id,
            date=local_date,
            timezone=self.office_timezone,
            day_start=day_start,
            day_end=day_end,
            occupied=[
                OccupiedInterval(start_at=booking.start_at, end_at=booking.end_at)
                for booking in bookings
            ],
        )

    async def free_rooms(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
        min_capacity: int | None = None,
    ) -> AvailabilityResponse:
        validate_interval(start_at=start_at, end_at=end_at)
        rooms = await self.rooms.list_free_active(
            start_at=start_at,
            end_at=end_at,
            min_capacity=min_capacity,
        )
        return AvailabilityResponse(
            start_at=start_at,
            end_at=end_at,
            rooms=[available_room(room) for room in rooms],
        )

    async def conflict_details(
        self,
        *,
        room_id: UUID,
        start_at: datetime,
        end_at: datetime,
        participants_count: int | None,
    ) -> BookingConflictDetails:
        requested_room = await self.rooms.get_active_by_id(room_id)
        if requested_room is None:
            raise room_not_found()
        minimum_capacity = participants_count or requested_room.capacity
        alternatives = await self.rooms.list_free_active(
            start_at=start_at,
            end_at=end_at,
            min_capacity=minimum_capacity,
            exclude_room_id=room_id,
            limit=ALTERNATIVE_LIMIT,
        )
        if alternatives:
            return BookingConflictDetails(
                alternative_rooms=[
                    AlternativeRoom(
                        **available_room(room).model_dump(),
                        start_at=start_at,
                        end_at=end_at,
                    )
                    for room in alternatives
                ],
                alternative_slots=[],
            )
        return BookingConflictDetails(
            alternative_rooms=[],
            alternative_slots=await self.nearest_slots(
                room_id=room_id,
                start_at=start_at,
                end_at=end_at,
            ),
        )

    async def nearest_slots(
        self,
        *,
        room_id: UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> list[AlternativeSlot]:
        validate_interval(start_at=start_at, end_at=end_at)
        room = await self.rooms.get_active_by_id(room_id)
        if room is None:
            raise room_not_found()
        search_end = start_at + SLOT_SEARCH_HORIZON
        bookings = await self.bookings.list_confirmed_overlapping(
            room_id=room_id,
            start_at=start_at,
            end_at=search_end,
        )
        intervals = [(booking.start_at, booking.end_at) for booking in bookings]
        return [
            AlternativeSlot(room_id=room_id, start_at=slot_start, end_at=slot_end)
            for slot_start, slot_end in nearest_available_slots(
                start_at=start_at,
                end_at=end_at,
                occupied=intervals,
            )
        ]


def available_room(room: Room) -> AvailableRoom:
    return AvailableRoom(room_id=room.id, name=room.name, capacity=room.capacity)


def local_day_bounds(local_date: date, timezone_name: str) -> tuple[datetime, datetime]:
    timezone = ZoneInfo(timezone_name)
    next_date = local_date + timedelta(days=1)
    return (
        datetime.combine(local_date, time.min, tzinfo=timezone),
        datetime.combine(next_date, time.min, tzinfo=timezone),
    )


def nearest_available_slots(
    *,
    start_at: datetime,
    end_at: datetime,
    occupied: list[tuple[datetime, datetime]],
    limit: int = ALTERNATIVE_LIMIT,
) -> list[tuple[datetime, datetime]]:
    validate_interval(start_at=start_at, end_at=end_at)
    duration = end_at - start_at
    search_end = start_at + SLOT_SEARCH_HORIZON
    candidate_start = start_at + SLOT_GRANULARITY
    slots: list[tuple[datetime, datetime]] = []
    while len(slots) < limit:
        candidate_end = candidate_start + duration
        if candidate_end > search_end:
            break
        if not any(
            occupied_start < candidate_end and occupied_end > candidate_start
            for occupied_start, occupied_end in occupied
        ):
            slots.append((candidate_start, candidate_end))
        candidate_start += SLOT_GRANULARITY
    return slots


def validate_interval(*, start_at: datetime, end_at: datetime) -> None:
    if not is_timezone_aware(start_at) or not is_timezone_aware(end_at):
        raise AppError(
            status_code=422,
            code="timezone_required",
            message="Booking start and end must include a timezone offset.",
        )
    if end_at <= start_at:
        raise AppError(
            status_code=422,
            code="invalid_booking_interval",
            message="Booking end must be after its start.",
        )


def is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def room_not_found() -> AppError:
    return AppError(status_code=404, code="room_not_found", message="Room was not found.")
