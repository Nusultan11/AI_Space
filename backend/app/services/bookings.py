"""Single business-logic path for booking mutations and protected reads."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.booking import Booking, BookingStatus
from app.models.room import Room
from app.models.user import User
from app.repositories.bookings import BookingsRepository
from app.repositories.rooms import RoomsRepository
from app.schemas.availability import BookingConflictDetails
from app.services.availability import AvailabilityService, validate_interval

BOOKING_OVERLAP_CONSTRAINT = "excl_bookings_room_time_confirmed"


class BookingService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.session = session
        self.bookings = BookingsRepository(session)
        self.rooms = RoomsRepository(session)
        self.availability = AvailabilityService(session)
        self.clock = clock or (lambda: datetime.now(UTC))

    async def create(
        self,
        *,
        user: User,
        room_id: UUID,
        title: str,
        start_at: datetime,
        end_at: datetime,
        participants_count: int | None,
    ) -> Booking:
        room = await self.rooms.get_active_by_id(room_id)
        if room is None:
            raise room_not_found()
        validate_booking_request(
            room=room,
            start_at=start_at,
            end_at=end_at,
            participants_count=participants_count,
            now=self.clock(),
        )
        if await self.bookings.has_confirmed_overlap(
            room_id=room_id,
            start_at=start_at,
            end_at=end_at,
        ):
            details = await self.availability.conflict_details(
                room_id=room_id,
                start_at=start_at,
                end_at=end_at,
                participants_count=participants_count,
            )
            raise booking_conflict(details)

        try:
            booking = await self.bookings.add(
                room_id=room_id,
                user_id=user.id,
                title=title,
                start_at=start_at,
                end_at=end_at,
                participants_count=participants_count,
            )
            await self.session.commit()
            await self.session.refresh(booking)
            return booking
        except IntegrityError as exc:
            constraint_name = integrity_constraint_name(exc)
            await self.session.rollback()
            if constraint_name == BOOKING_OVERLAP_CONSTRAINT:
                details = await self.availability.conflict_details(
                    room_id=room_id,
                    start_at=start_at,
                    end_at=end_at,
                    participants_count=participants_count,
                )
                raise booking_conflict(details) from None
            raise

    async def list_for_user(self, user: User) -> list[Booking]:
        return await self.bookings.list_for_user(user.id)

    async def get_for_user(self, *, booking_id: UUID, user: User) -> Booking:
        booking = await self.bookings.get_for_user(booking_id=booking_id, user_id=user.id)
        if booking is None:
            raise booking_not_found()
        return booking

    async def cancel(self, *, booking_id: UUID, user: User) -> Booking:
        booking = await self.get_for_user(booking_id=booking_id, user=user)
        if booking.status == BookingStatus.CANCELLED:
            raise booking_already_cancelled()
        await self.bookings.cancel(booking, cancelled_at=self.clock())
        await self.session.commit()
        await self.session.refresh(booking)
        return booking


def validate_booking_request(
    *,
    room: Room,
    start_at: datetime,
    end_at: datetime,
    participants_count: int | None,
    now: datetime,
) -> None:
    validate_interval(start_at=start_at, end_at=end_at)
    if start_at < now:
        raise AppError(
            status_code=422,
            code="booking_in_past",
            message="Booking start cannot be in the past.",
        )
    if participants_count is not None and participants_count < 1:
        raise AppError(
            status_code=422,
            code="invalid_participants_count",
            message="Participant count must be at least one.",
        )
    if participants_count is not None and participants_count > room.capacity:
        raise AppError(
            status_code=422,
            code="room_capacity_exceeded",
            message="Participant count exceeds room capacity.",
            details={"room_capacity": room.capacity},
        )


def integrity_constraint_name(exc: IntegrityError) -> str | None:
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        name = getattr(current, "constraint_name", None)
        if isinstance(name, str):
            return name
        diagnostic = getattr(current, "diag", None)
        name = getattr(diagnostic, "constraint_name", None)
        if isinstance(name, str):
            return name
        current = current.__cause__ or current.__context__
    if BOOKING_OVERLAP_CONSTRAINT in str(exc):
        return BOOKING_OVERLAP_CONSTRAINT
    return None


def room_not_found() -> AppError:
    return AppError(status_code=404, code="room_not_found", message="Room was not found.")


def booking_not_found() -> AppError:
    return AppError(status_code=404, code="booking_not_found", message="Booking was not found.")


def booking_conflict(details: BookingConflictDetails) -> AppError:
    return AppError(
        status_code=409,
        code="booking_conflict",
        message="The room is already booked for this time.",
        details=details.model_dump(mode="json"),
    )


def booking_already_cancelled() -> AppError:
    return AppError(
        status_code=409,
        code="booking_already_cancelled",
        message="Booking is already cancelled.",
    )
