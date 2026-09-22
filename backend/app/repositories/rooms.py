"""Explicit room catalog queries."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.room import Room


class RoomsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(self) -> list[Room]:
        result = await self.session.scalars(
            select(Room).where(Room.is_active.is_(True)).order_by(Room.name, Room.id)
        )
        return list(result)

    async def get_active_by_id(self, room_id: UUID) -> Room | None:
        return await self.session.scalar(
            select(Room).where(Room.id == room_id, Room.is_active.is_(True))
        )

    async def list_free_active(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
        min_capacity: int | None = None,
        exclude_room_id: UUID | None = None,
        limit: int | None = None,
    ) -> list[Room]:
        overlap_exists = (
            select(Booking.id)
            .where(
                Booking.room_id == Room.id,
                Booking.status == BookingStatus.CONFIRMED,
                Booking.start_at < end_at,
                Booking.end_at > start_at,
            )
            .correlate(Room)
            .exists()
        )
        statement = select(Room).where(Room.is_active.is_(True), ~overlap_exists)
        if min_capacity is not None:
            statement = statement.where(Room.capacity >= min_capacity)
        if exclude_room_id is not None:
            statement = statement.where(Room.id != exclude_room_id)
        statement = statement.order_by(Room.capacity, Room.name, Room.id)
        if limit is not None:
            statement = statement.limit(limit)
        return list(await self.session.scalars(statement))
