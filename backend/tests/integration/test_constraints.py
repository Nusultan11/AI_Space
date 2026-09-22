from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.room import Room
from app.models.user import User


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgresql_enforces_user_email_and_room_capacity_constraints(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        session.add(
            User(
                id=uuid4(),
                email="Not-Normalized@example.com",
                name="Invalid",
                password_hash="not-plaintext-but-not-used",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

        session.add(Room(id=uuid4(), name="Invalid capacity", capacity=0))
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

        session.add_all(
            [
                User(
                    id=uuid4(),
                    email="duplicate@example.com",
                    name="First",
                    password_hash="hash-one",
                ),
                User(
                    id=uuid4(),
                    email="duplicate@example.com",
                    name="Second",
                    password_hash="hash-two",
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
