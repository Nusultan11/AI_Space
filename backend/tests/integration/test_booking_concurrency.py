from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.models.booking import Booking, BookingStatus
from app.models.room import Room
from app.repositories.bookings import BookingsRepository

JWT_SECRET = "booking-concurrency-secret-with-sufficient-length"


@pytest.fixture
async def client(
    database_engine: AsyncEngine,
    migrated_database,
) -> AsyncIterator[AsyncClient]:
    settings = Settings(
        app_env="test",
        database_url=migrated_database.async_url,
        jwt_secret=SecretStr(JWT_SECRET),
    )
    app = create_app(settings, database_engine)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        yield http_client


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_identical_requests_leave_one_confirmed_booking(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "race@example.com",
            "name": "Race User",
            "password": "correct-password",
        },
    )
    assert registered.status_code == 201
    logged_in = await client.post(
        "/api/v1/auth/login",
        json={"email": "race@example.com", "password": "correct-password"},
    )
    headers = {"Authorization": f"Bearer {logged_in.json()['access_token']}"}
    async with session_factory() as session:
        room = Room(name="Concurrency room", capacity=4)
        session.add(room)
        await session.commit()
        await session.refresh(room)

    start_at = datetime.now(UTC) + timedelta(days=3)
    payload = {
        "room_id": str(room.id),
        "title": "Concurrent booking",
        "start_at": start_at.isoformat(),
        "end_at": (start_at + timedelta(hours=1)).isoformat(),
        "participants_count": 2,
    }

    responses = await asyncio.gather(
        client.post("/api/v1/bookings", json=payload, headers=headers),
        client.post("/api/v1/bookings", json=payload, headers=headers),
    )

    assert sorted(response.status_code for response in responses) == [201, 409]
    conflict = next(response for response in responses if response.status_code == 409)
    assert conflict.json()["error"]["code"] == "booking_conflict"
    async with session_factory() as session:
        confirmed_count = await session.scalar(
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.room_id == room.id,
                Booking.start_at == start_at,
                Booking.status == BookingStatus.CONFIRMED,
            )
        )
    assert confirmed_count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_cancellation_has_one_winner(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "cancel-race@example.com",
            "name": "Cancel Racer",
            "password": "correct-password",
        },
    )
    assert registered.status_code == 201
    logged_in = await client.post(
        "/api/v1/auth/login",
        json={"email": "cancel-race@example.com", "password": "correct-password"},
    )
    headers = {"Authorization": f"Bearer {logged_in.json()['access_token']}"}
    async with session_factory() as session:
        room = Room(name="Cancellation race room", capacity=4)
        session.add(room)
        await session.commit()
        await session.refresh(room)
    start_at = datetime.now(UTC) + timedelta(days=3)
    created = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": str(room.id),
            "title": "Cancel once",
            "start_at": start_at.isoformat(),
            "end_at": (start_at + timedelta(hours=1)).isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201
    booking_id = created.json()["id"]

    original_get = BookingsRepository.get_for_user_for_update
    both_started = asyncio.Event()
    contenders = 0

    async def synchronized_get(self, *, booking_id, user_id):
        nonlocal contenders
        contenders += 1
        if contenders == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), timeout=5)
        return await original_get(self, booking_id=booking_id, user_id=user_id)

    monkeypatch.setattr(BookingsRepository, "get_for_user_for_update", synchronized_get)
    responses = await asyncio.gather(
        client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=headers),
        client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=headers),
    )
    assert sorted(response.status_code for response in responses) == [200, 409]
    conflict = next(response for response in responses if response.status_code == 409)
    assert conflict.json()["error"]["code"] == "booking_already_cancelled"
