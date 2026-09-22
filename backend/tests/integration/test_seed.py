from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.seed import DEMO_ROOMS, seed_rooms
from app.models.room import Room


@pytest.mark.integration
@pytest.mark.asyncio
async def test_room_seed_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await seed_rooms(session)
        await seed_rooms(session)
        count = await session.scalar(select(func.count()).select_from(Room))
        rooms = list(await session.scalars(select(Room).order_by(Room.name)))

    assert count == 3
    assert {(room.name, room.capacity) for room in rooms} == {
        (room["name"], room["capacity"]) for room in DEMO_ROOMS
    }
