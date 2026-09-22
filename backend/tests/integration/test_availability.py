from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

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

JWT_SECRET = "availability-integration-secret-with-sufficient-length"
OFFICE_TIMEZONE = "Asia/Almaty"


def _settings(database_url: str) -> Settings:
    return Settings(
        app_env="test",
        database_url=database_url,
        jwt_secret=SecretStr(JWT_SECRET),
        office_timezone=OFFICE_TIMEZONE,
    )


@pytest.fixture
async def client(
    database_engine: AsyncEngine,
    migrated_database,
) -> AsyncIterator[AsyncClient]:
    app = create_app(_settings(migrated_database.async_url), database_engine)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        yield http_client


async def _identity(client: AsyncClient, email: str) -> tuple[UUID, dict[str, str]]:
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Availability User", "password": "correct-password"},
    )
    assert registered.status_code == 201, registered.text
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-password"},
    )
    assert login.status_code == 200, login.text
    return UUID(registered.json()["id"]), {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


async def _rooms(
    session_factory: async_sessionmaker[AsyncSession],
    *rooms: Room,
) -> tuple[Room, ...]:
    async with session_factory() as session:
        session.add_all(rooms)
        await session.commit()
        for room in rooms:
            await session.refresh(room)
    return rooms


async def _booking(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    user_id: UUID,
    room_id: UUID,
    start_at: datetime,
    end_at: datetime,
    status: BookingStatus = BookingStatus.CONFIRMED,
    title: str = "Private meeting",
) -> Booking:
    async with session_factory() as session:
        booking = Booking(
            user_id=user_id,
            room_id=room_id,
            title=title,
            start_at=start_at,
            end_at=end_at,
            status=status,
            cancelled_at=datetime.now(UTC) if status == BookingStatus.CANCELLED else None,
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)
        return booking


def _booking_payload(
    room_id: UUID,
    start_at: datetime,
    end_at: datetime,
    *,
    participants_count: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "room_id": str(room_id),
        "title": "Requested meeting",
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
    }
    if participants_count is not None:
        payload["participants_count"] = participants_count
    return payload


@pytest.mark.integration
@pytest.mark.asyncio
async def test_room_schedule_is_private_local_day_and_ignores_cancelled(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user_id, headers = await _identity(client, "schedule@example.com")
    room, inactive = await _rooms(
        session_factory,
        Room(name="Schedule room", capacity=4),
        Room(name="Inactive schedule room", capacity=4, is_active=False),
    )
    zone = ZoneInfo(OFFICE_TIMEZONE)
    local_date = date(2030, 1, 2)
    confirmed_start = datetime.combine(local_date, time(10), tzinfo=zone)
    crossing_start = datetime.combine(local_date, time(23, 30), tzinfo=zone)
    crossing_end = datetime.combine(local_date + timedelta(days=1), time(0, 30), tzinfo=zone)
    await _booking(
        session_factory,
        user_id=user_id,
        room_id=room.id,
        start_at=confirmed_start,
        end_at=confirmed_start + timedelta(hours=1),
        title="Sensitive title",
    )
    await _booking(
        session_factory,
        user_id=user_id,
        room_id=room.id,
        start_at=crossing_start,
        end_at=crossing_end,
    )
    await _booking(
        session_factory,
        user_id=user_id,
        room_id=room.id,
        start_at=confirmed_start + timedelta(hours=2),
        end_at=confirmed_start + timedelta(hours=3),
        status=BookingStatus.CANCELLED,
    )

    schedule = await client.get(
        f"/api/v1/rooms/{room.id}/schedule",
        params={"date": local_date.isoformat()},
        headers=headers,
    )
    next_schedule = await client.get(
        f"/api/v1/rooms/{room.id}/schedule",
        params={"date": (local_date + timedelta(days=1)).isoformat()},
        headers=headers,
    )
    empty_schedule = await client.get(
        f"/api/v1/rooms/{room.id}/schedule",
        params={"date": (local_date - timedelta(days=1)).isoformat()},
        headers=headers,
    )
    inactive_response = await client.get(
        f"/api/v1/rooms/{inactive.id}/schedule",
        params={"date": local_date.isoformat()},
        headers=headers,
    )
    missing_response = await client.get(
        f"/api/v1/rooms/{uuid4()}/schedule",
        params={"date": local_date.isoformat()},
        headers=headers,
    )

    assert schedule.status_code == 200
    assert schedule.json()["timezone"] == OFFICE_TIMEZONE
    assert len(schedule.json()["occupied"]) == 2
    assert set(schedule.json()["occupied"][0]) == {"start_at", "end_at"}
    assert all(
        "title" not in item and "user_id" not in item for item in schedule.json()["occupied"]
    )
    assert len(next_schedule.json()["occupied"]) == 1
    assert empty_schedule.json()["occupied"] == []
    assert inactive_response.status_code == 404
    assert missing_response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_free_rooms_use_half_open_overlap_capacity_and_deterministic_order(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user_id, headers = await _identity(client, "free@example.com")
    small, alpha, beta, _large, inactive = await _rooms(
        session_factory,
        Room(name="Small", capacity=2),
        Room(name="Alpha", capacity=4),
        Room(name="Beta", capacity=4),
        Room(name="Large", capacity=8),
        Room(name="Inactive", capacity=1, is_active=False),
    )
    start_at = datetime(2030, 2, 1, 10, 0, tzinfo=UTC)
    end_at = start_at + timedelta(hours=1)
    await _booking(
        session_factory,
        user_id=user_id,
        room_id=beta.id,
        start_at=start_at + timedelta(minutes=30),
        end_at=end_at + timedelta(minutes=30),
    )
    await _booking(
        session_factory,
        user_id=user_id,
        room_id=alpha.id,
        start_at=start_at - timedelta(hours=1),
        end_at=start_at,
    )
    await _booking(
        session_factory,
        user_id=user_id,
        room_id=small.id,
        start_at=start_at,
        end_at=end_at,
        status=BookingStatus.CANCELLED,
    )

    available = await client.get(
        "/api/v1/availability",
        params={"start_at": start_at.isoformat(), "end_at": end_at.isoformat()},
        headers=headers,
    )
    capacity_filtered = await client.get(
        "/api/v1/availability",
        params={
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "min_capacity": 4,
        },
        headers=headers,
    )
    invalid = await client.get(
        "/api/v1/availability",
        params={"start_at": end_at.isoformat(), "end_at": start_at.isoformat()},
        headers=headers,
    )
    naive = await client.get(
        "/api/v1/availability",
        params={
            "start_at": start_at.replace(tzinfo=None).isoformat(),
            "end_at": end_at.isoformat(),
        },
        headers=headers,
    )

    assert available.status_code == 200
    assert [room["name"] for room in available.json()["rooms"]] == ["Small", "Alpha", "Large"]
    assert [room["name"] for room in capacity_filtered.json()["rooms"]] == ["Alpha", "Large"]
    assert all(room["name"] != inactive.name for room in available.json()["rooms"])
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_booking_interval"
    assert naive.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_precheck_conflict_prefers_best_fit_rooms_and_uses_shared_shape(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user_id, headers = await _identity(client, "alternatives@example.com")
    original, small, _zeta, _alpha, _large = await _rooms(
        session_factory,
        Room(name="Original", capacity=6),
        Room(name="Too small", capacity=2),
        Room(name="Zeta", capacity=4),
        Room(name="Alpha alternative", capacity=4),
        Room(name="Large alternative", capacity=6),
    )
    start_at = datetime(2030, 3, 1, 10, 0, tzinfo=UTC)
    end_at = start_at + timedelta(hours=1)
    await _booking(
        session_factory,
        user_id=user_id,
        room_id=original.id,
        start_at=start_at,
        end_at=end_at,
    )

    omitted_count_response = await client.post(
        "/api/v1/bookings",
        json=_booking_payload(original.id, start_at, end_at),
        headers=headers,
    )
    known_count_response = await client.post(
        "/api/v1/bookings",
        json=_booking_payload(original.id, start_at, end_at, participants_count=4),
        headers=headers,
    )

    assert omitted_count_response.status_code == 409
    omitted_details = omitted_count_response.json()["error"]["details"]
    assert [room["name"] for room in omitted_details["alternative_rooms"]] == ["Large alternative"]
    assert known_count_response.status_code == 409
    details = known_count_response.json()["error"]["details"]
    assert set(details) == {"alternative_rooms", "alternative_slots"}
    assert [room["name"] for room in details["alternative_rooms"]] == [
        "Alpha alternative",
        "Zeta",
        "Large alternative",
    ]
    assert all(room["room_id"] != str(small.id) for room in details["alternative_rooms"])
    assert all(
        room["start_at"] == start_at.isoformat().replace("+00:00", "Z")
        for room in details["alternative_rooms"]
    )
    assert details["alternative_slots"] == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_conflict_falls_back_to_exact_duration_nearest_slots(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user_id, headers = await _identity(client, "slots@example.com")
    (room,) = await _rooms(session_factory, Room(name="Only room", capacity=4))
    start_at = datetime(2030, 4, 1, 10, 0, tzinfo=UTC)
    end_at = start_at + timedelta(hours=1)
    await _booking(
        session_factory,
        user_id=user_id,
        room_id=room.id,
        start_at=start_at,
        end_at=end_at,
    )

    response = await client.post(
        "/api/v1/bookings",
        json=_booking_payload(room.id, start_at, end_at),
        headers=headers,
    )

    assert response.status_code == 409
    details = response.json()["error"]["details"]
    assert details["alternative_rooms"] == []
    slots = details["alternative_slots"]
    assert [datetime.fromisoformat(slot["start_at"]) for slot in slots] == [
        end_at,
        end_at + timedelta(minutes=15),
        end_at + timedelta(minutes=30),
    ]
    assert all(
        datetime.fromisoformat(slot["end_at"]) - datetime.fromisoformat(slot["start_at"])
        == timedelta(hours=1)
        for slot in slots
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_race_conflict_rolls_back_before_shared_alternatives(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, headers = await _identity(client, "race-availability@example.com")
    original, alternative = await _rooms(
        session_factory,
        Room(name="Race original", capacity=4),
        Room(name="Race alternative", capacity=4),
    )

    async def bypass_precheck(
        _repository: BookingsRepository,
        *,
        room_id: UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> bool:
        return False

    monkeypatch.setattr(BookingsRepository, "has_confirmed_overlap", bypass_precheck)
    start_at = datetime(2030, 5, 1, 10, 0, tzinfo=UTC)
    end_at = start_at + timedelta(hours=1)
    payload = _booking_payload(original.id, start_at, end_at, participants_count=4)

    responses = await asyncio.gather(
        client.post("/api/v1/bookings", json=payload, headers=headers),
        client.post("/api/v1/bookings", json=payload, headers=headers),
    )

    assert sorted(response.status_code for response in responses) == [201, 409]
    conflict = next(response for response in responses if response.status_code == 409)
    details = conflict.json()["error"]["details"]
    assert set(details) == {"alternative_rooms", "alternative_slots"}
    assert [room["room_id"] for room in details["alternative_rooms"]] == [str(alternative.id)]
    async with session_factory() as session:
        confirmed = await session.scalar(
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.room_id == original.id,
                Booking.status == BookingStatus.CONFIRMED,
            )
        )
    assert confirmed == 1
