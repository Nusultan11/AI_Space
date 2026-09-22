"""Idempotent local/review seed for the required demo rooms."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import create_database_engine, create_session_factory
from app.models.room import Room

DEMO_ROOMS = (
    {"name": "Большая переговорная", "capacity": 12},
    {"name": "Средняя переговорная", "capacity": 6},
    {"name": "Малая переговорная", "capacity": 4},
)


async def seed_rooms(session: AsyncSession) -> None:
    statement = insert(Room).values(
        [
            {
                "id": uuid4(),
                "name": room["name"],
                "capacity": room["capacity"],
                "is_active": True,
            }
            for room in DEMO_ROOMS
        ]
    )
    await session.execute(statement.on_conflict_do_nothing(index_elements=[Room.name]))
    await session.commit()


async def main() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            await seed_rooms(session)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
