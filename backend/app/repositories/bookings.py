"""Explicit booking persistence operations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus


class BookingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        room_id: UUID,
        user_id: UUID,
        title: str,
        start_at: datetime,
        end_at: datetime,
        participants_count: int | None,
    ) -> Booking:
        booking = Booking(
            room_id=room_id,
            user_id=user_id,
            title=title,
            start_at=start_at,
            end_at=end_at,
            participants_count=participants_count,
        )
        self.session.add(booking)
        await self.session.flush()
        return booking

    async def list_for_user(self, user_id: UUID) -> list[Booking]:
        result = await self.session.scalars(select(Booking).where(Booking.user_id == user_id))
        return list(result)

    async def get_for_user(self, *, booking_id: UUID, user_id: UUID) -> Booking | None:
        return await self.session.scalar(
            select(Booking).where(Booking.id == booking_id, Booking.user_id == user_id)
        )

    async def has_confirmed_overlap(
        self,
        *,
        room_id: UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> bool:
        booking_id = await self.session.scalar(
            select(Booking.id)
            .where(
                Booking.room_id == room_id,
                Booking.status == BookingStatus.CONFIRMED,
                Booking.start_at < end_at,
                Booking.end_at > start_at,
            )
            .limit(1)
        )
        return booking_id is not None

    async def cancel(self, booking: Booking, *, cancelled_at: datetime) -> None:
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = cancelled_at
        await self.session.flush()
