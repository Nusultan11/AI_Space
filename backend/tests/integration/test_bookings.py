from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.models.booking import Booking, BookingStatus
from app.models.room import Room
from app.models.user import User
from app.services.bookings import BOOKING_OVERLAP_CONSTRAINT, integrity_constraint_name

JWT_SECRET = "booking-integration-secret-with-sufficient-length"


def _settings(database_url: str) -> Settings:
    return Settings(
        app_env="test",
        database_url=database_url,
        jwt_secret=SecretStr(JWT_SECRET),
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


async def _register_and_login(client: AsyncClient, email: str) -> tuple[UUID, dict[str, str]]:
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Booking User", "password": "correct-password"},
    )
    assert registered.status_code == 201, registered.text
    logged_in = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-password"},
    )
    assert logged_in.status_code == 200, logged_in.text
    return UUID(registered.json()["id"]), {
        "Authorization": f"Bearer {logged_in.json()['access_token']}"
    }


async def _add_room(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    name: str = "Booking room",
    capacity: int = 4,
    active: bool = True,
) -> Room:
    async with session_factory() as session:
        room = Room(name=name, capacity=capacity, is_active=active)
        session.add(room)
        await session.commit()
        await session.refresh(room)
        return room


def _payload(room_id: UUID, start_at: datetime, end_at: datetime) -> dict[str, object]:
    return {
        "room_id": str(room_id),
        "title": "Planning",
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "participants_count": 3,
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_booking_api_create_list_read_cancel_and_ownership(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner_id, owner_headers = await _register_and_login(client, "owner@example.com")
    _, other_headers = await _register_and_login(client, "other@example.com")
    room = await _add_room(session_factory)
    start_at = datetime.now(UTC) + timedelta(days=1)
    end_at = start_at + timedelta(hours=1)

    created = await client.post(
        "/api/v1/bookings",
        json=_payload(room.id, start_at, end_at),
        headers=owner_headers,
    )
    assert created.status_code == 201, created.text
    booking_id = created.json()["id"]
    assert created.json()["user_id"] == str(owner_id)
    assert created.json()["status"] == "confirmed"

    listed = await client.get("/api/v1/bookings", headers=owner_headers)
    other_listed = await client.get("/api/v1/bookings", headers=other_headers)
    detail = await client.get(f"/api/v1/bookings/{booking_id}", headers=owner_headers)
    hidden = await client.get(f"/api/v1/bookings/{booking_id}", headers=other_headers)
    forbidden_cancel = await client.post(
        f"/api/v1/bookings/{booking_id}/cancel", headers=other_headers
    )
    overlap = await client.post(
        "/api/v1/bookings",
        json=_payload(room.id, start_at + timedelta(minutes=30), end_at + timedelta(minutes=30)),
        headers=owner_headers,
    )

    assert [booking["id"] for booking in listed.json()] == [booking_id]
    assert other_listed.json() == []
    assert detail.status_code == 200
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "booking_not_found"
    assert forbidden_cancel.status_code == 404
    assert overlap.status_code == 409
    assert overlap.json()["error"]["code"] == "booking_conflict"

    cancelled = await client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=owner_headers)
    repeated = await client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=owner_headers)
    replacement = await client.post(
        "/api/v1/bookings",
        json=_payload(room.id, start_at, end_at),
        headers=owner_headers,
    )

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_at"] is not None
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "booking_already_cancelled"
    assert replacement.status_code == 201, replacement.text
    async with session_factory() as session:
        stored = await session.get(Booking, UUID(booking_id))
        assert stored is not None
        assert stored.status == BookingStatus.CANCELLED


@pytest.mark.integration
@pytest.mark.asyncio
async def test_booking_api_validates_times_capacity_and_server_owned_fields(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _, headers = await _register_and_login(client, "validation@example.com")
    room = await _add_room(session_factory, capacity=2)
    inactive_room = await _add_room(
        session_factory,
        name="Inactive booking room",
        active=False,
    )
    start_at = datetime.now(UTC) + timedelta(days=1)
    valid = _payload(room.id, start_at, start_at + timedelta(hours=1))

    over_capacity = dict(valid, participants_count=3)
    past = _payload(
        room.id,
        datetime.now(UTC) - timedelta(hours=2),
        datetime.now(UTC) - timedelta(hours=1),
    )
    invalid_interval = _payload(room.id, start_at, start_at)
    naive = dict(valid, start_at=start_at.replace(tzinfo=None).isoformat())
    client_owned = dict(valid, user_id=str(uuid4()), status="cancelled")
    inactive = _payload(inactive_room.id, start_at, start_at + timedelta(hours=1))
    missing = _payload(uuid4(), start_at, start_at + timedelta(hours=1))

    responses = {
        "capacity": await client.post("/api/v1/bookings", json=over_capacity, headers=headers),
        "past": await client.post("/api/v1/bookings", json=past, headers=headers),
        "interval": await client.post("/api/v1/bookings", json=invalid_interval, headers=headers),
        "naive": await client.post("/api/v1/bookings", json=naive, headers=headers),
        "owned": await client.post("/api/v1/bookings", json=client_owned, headers=headers),
        "inactive": await client.post("/api/v1/bookings", json=inactive, headers=headers),
        "missing": await client.post("/api/v1/bookings", json=missing, headers=headers),
    }

    assert responses["capacity"].status_code == 422
    assert responses["capacity"].json()["error"]["code"] == "room_capacity_exceeded"
    assert responses["past"].status_code == 422
    assert responses["past"].json()["error"]["code"] == "booking_in_past"
    assert responses["interval"].status_code == 422
    assert responses["interval"].json()["error"]["code"] == "invalid_booking_interval"
    assert responses["naive"].status_code == 422
    assert responses["owned"].status_code == 422
    assert responses["inactive"].status_code == 404
    assert responses["inactive"].json()["error"]["code"] == "room_not_found"
    assert responses["missing"].status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_booking_title_boundary(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _, headers = await _register_and_login(client, "title-boundary@example.com")
    room = await _add_room(session_factory)
    start_at = datetime.now(UTC) + timedelta(days=1)
    payload = _payload(room.id, start_at, start_at + timedelta(hours=1))
    accepted = await client.post(
        "/api/v1/bookings", json={**payload, "title": "x" * 200}, headers=headers
    )
    rejected = await client.post(
        "/api/v1/bookings", json={**payload, "title": "x" * 201}, headers=headers
    )
    assert accepted.status_code == 201, accepted.text
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_personal_booking_list_has_stable_start_and_id_order(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _, headers = await _register_and_login(client, "listing-order@example.com")
    first_room = await _add_room(session_factory, name="First order room")
    second_room = await _add_room(session_factory, name="Second order room")
    start_at = datetime.now(UTC) + timedelta(days=3)
    created = []
    for room_id, offset in [
        (first_room.id, 60),
        (first_room.id, 0),
        (second_room.id, 0),
    ]:
        slot_start = start_at + timedelta(minutes=offset)
        response = await client.post(
            "/api/v1/bookings",
            json=_payload(room_id, slot_start, slot_start + timedelta(minutes=30)),
            headers=headers,
        )
        assert response.status_code == 201, response.text
        created.append(response.json())
    listed = await client.get("/api/v1/bookings", headers=headers)
    assert listed.status_code == 200
    expected = sorted(created, key=lambda booking: (booking["start_at"], booking["id"]))
    assert [booking["id"] for booking in listed.json()] == [booking["id"] for booking in expected]


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "start_minutes", "end_minutes", "other_room", "cancel_first", "conflict"),
    [
        ("identical", 0, 60, False, False, True),
        ("left_overlap", -30, 30, False, False, True),
        ("right_overlap", 30, 90, False, False, True),
        ("inside", 15, 45, False, False, True),
        ("enclosing", -15, 75, False, False, True),
        ("adjacent_before", -60, 0, False, False, False),
        ("adjacent_after", 60, 120, False, False, False),
        ("other_room", 0, 60, True, False, False),
        ("cancelled_first", 0, 60, False, True, False),
    ],
)
async def test_postgresql_overlap_matrix(
    session_factory: async_sessionmaker[AsyncSession],
    case: str,
    start_minutes: int,
    end_minutes: int,
    other_room: bool,
    cancel_first: bool,
    conflict: bool,
) -> None:
    async with session_factory() as session:
        user = User(email=f"matrix-{case}@example.com", name="Matrix User", password_hash="unused")
        room = Room(name=f"Matrix room {case}", capacity=4)
        alternate = Room(name=f"Alternate matrix room {case}", capacity=4)
        session.add_all([user, room, alternate])
        await session.commit()
        start_at = datetime.now(UTC) + timedelta(days=2)
        original = Booking(
            room_id=room.id,
            user_id=user.id,
            title="Original",
            start_at=start_at,
            end_at=start_at + timedelta(hours=1),
            status=BookingStatus.CANCELLED if cancel_first else BookingStatus.CONFIRMED,
        )
        session.add(original)
        await session.commit()
        session.add(
            Booking(
                room_id=alternate.id if other_room else room.id,
                user_id=user.id,
                title="Candidate",
                start_at=start_at + timedelta(minutes=start_minutes),
                end_at=start_at + timedelta(minutes=end_minutes),
            )
        )
        if conflict:
            with pytest.raises(IntegrityError) as error:
                await session.commit()
            assert integrity_constraint_name(error.value) == BOOKING_OVERLAP_CONSTRAINT
            await session.rollback()
        else:
            await session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgresql_booking_exclusion_constraint_and_boundaries(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = User(
            email="constraint@example.com",
            name="Constraint User",
            password_hash="not-used",
        )
        room = Room(name="Constraint room", capacity=4)
        other_room = Room(name="Other constraint room", capacity=4)
        session.add_all([user, room, other_room])
        await session.commit()
        await session.refresh(user)
        await session.refresh(room)
        await session.refresh(other_room)

        start_at = datetime.now(UTC) + timedelta(days=2)
        end_at = start_at + timedelta(hours=1)
        session.add(
            Booking(
                room_id=room.id,
                user_id=user.id,
                title="First",
                start_at=start_at,
                end_at=end_at,
            )
        )
        await session.commit()

        session.add_all(
            [
                Booking(
                    room_id=room.id,
                    user_id=user.id,
                    title="Adjacent",
                    start_at=end_at,
                    end_at=end_at + timedelta(hours=1),
                ),
                Booking(
                    room_id=other_room.id,
                    user_id=user.id,
                    title="Other room",
                    start_at=start_at,
                    end_at=end_at,
                ),
            ]
        )
        await session.commit()

        session.add(
            Booking(
                room_id=room.id,
                user_id=user.id,
                title="Overlap",
                start_at=start_at + timedelta(minutes=30),
                end_at=end_at + timedelta(minutes=30),
            )
        )
        with pytest.raises(IntegrityError) as error:
            await session.commit()
        assert integrity_constraint_name(error.value) == BOOKING_OVERLAP_CONSTRAINT
        await session.rollback()

        constraint_exists = await session.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'excl_bookings_room_time_confirmed'
                      AND contype = 'x'
                )
                """
            )
        )
        assert constraint_exists is True

        bookings = list(await session.scalars(select(Booking)))
        assert {booking.title for booking in bookings} == {"First", "Adjacent", "Other room"}
