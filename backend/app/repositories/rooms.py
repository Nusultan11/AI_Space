"""Explicit room catalog queries."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
