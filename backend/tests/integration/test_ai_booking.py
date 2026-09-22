from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.v1.ai import get_booking_intent_parser
from app.core.config import Settings
from app.integrations.deepseek.fake import FakeBookingIntentParser
from app.integrations.deepseek.parser import ai_timeout
from app.main import create_app
from app.models.booking import Booking
from app.models.room import Room
from app.schemas.ai_booking import BookingIntent

JWT_SECRET = "ai-integration-secret-with-sufficient-length"


def _settings(database_url: str, *, api_key: str | None = None) -> Settings:
    return Settings(
        app_env="test",
        database_url=database_url,
        jwt_secret=SecretStr(JWT_SECRET),
        deepseek_api_key=SecretStr(api_key) if api_key is not None else None,
    )


def _app(
    database_url: str,
    engine: AsyncEngine,
    *,
    parser: FakeBookingIntentParser | None = None,
    api_key: str | None = None,
) -> FastAPI:
    app = create_app(_settings(database_url, api_key=api_key), engine)
    if parser is not None:
        app.dependency_overrides[get_booking_intent_parser] = lambda: parser
    return app


@asynccontextmanager
async def _client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


async def _identity(client: AsyncClient, email: str) -> tuple[UUID, dict[str, str]]:
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "AI User", "password": "correct-password"},
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


async def _room(session_factory: async_sessionmaker[AsyncSession]) -> Room:
    async with session_factory() as session:
        room = Room(name="AI room", capacity=4)
        session.add(room)
        await session.commit()
        await session.refresh(room)
        return room


def _valid_intent(room_id: UUID) -> BookingIntent:
    start_at = datetime.now(UTC) + timedelta(days=1)
    return BookingIntent(
        room_id=room_id,
        room_reference="AI room",
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
        title="AI preview",
        participants_count=2,
        needs_clarification=False,
        missing_fields=[],
        clarification_message=None,
    )


async def _booking_count(session_factory: async_sessionmaker[AsyncSession]) -> int:
    async with session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(Booking))
        return count or 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_authenticated_valid_and_clarification_previews_create_no_bookings(
    database_engine: AsyncEngine,
    migrated_database,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    room = await _room(session_factory)
    valid_parser = FakeBookingIntentParser(_valid_intent(room.id))
    app = _app(migrated_database.async_url, database_engine, parser=valid_parser)
    async with _client(app) as client:
        _, headers = await _identity(client, "preview@example.com")
        valid = await client.post(
            "/api/v1/ai/booking-intent",
            json={"text": "Book AI room tomorrow"},
            headers=headers,
        )
        unauthenticated = await client.post(
            "/api/v1/ai/booking-intent",
            json={"text": "Book AI room tomorrow"},
        )

    clarification_parser = FakeBookingIntentParser(
        BookingIntent(
            room_id=None,
            room_reference=None,
            start_at=None,
            end_at=None,
            title=None,
            participants_count=None,
            needs_clarification=True,
            missing_fields=["room_id", "start_at", "end_at", "title"],
            clarification_message="Which room and time?",
        )
    )
    clarification_app = _app(
        migrated_database.async_url,
        database_engine,
        parser=clarification_parser,
    )
    async with _client(clarification_app) as client:
        _, clarification_headers = await _identity(client, "clarification@example.com")
        clarification = await client.post(
            "/api/v1/ai/booking-intent",
            json={"text": "Book something after lunch"},
            headers=clarification_headers,
        )

    assert valid.status_code == 200
    assert valid.json()["room_id"] == str(room.id)
    assert valid.json()["needs_clarification"] is False
    assert unauthenticated.status_code == 401
    assert clarification.status_code == 200
    assert clarification.json()["needs_clarification"] is True
    assert await _booking_count(session_factory) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_provider_failure_creates_no_booking(
    database_engine: AsyncEngine,
    migrated_database,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _room(session_factory)
    app = _app(
        migrated_database.async_url,
        database_engine,
        parser=FakeBookingIntentParser(ai_timeout()),
    )
    async with _client(app) as client:
        _, headers = await _identity(client, "failure@example.com")
        response = await client.post(
            "/api/v1/ai/booking-intent",
            json={"text": "Book a room"},
            headers=headers,
        )

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "ai_timeout"
    assert await _booking_count(session_factory) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_missing_key_does_not_break_readiness_or_manual_booking(
    database_engine: AsyncEngine,
    migrated_database,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    room = await _room(session_factory)
    app = _app(migrated_database.async_url, database_engine)
    async with _client(app) as client:
        _, headers = await _identity(client, "fallback@example.com")
        ai_response = await client.post(
            "/api/v1/ai/booking-intent",
            json={"text": "Book AI room tomorrow"},
            headers=headers,
        )
        assert await _booking_count(session_factory) == 0
        start_at = datetime.now(UTC) + timedelta(days=2)
        manual = await client.post(
            "/api/v1/bookings",
            json={
                "room_id": str(room.id),
                "title": "Manual fallback",
                "start_at": start_at.isoformat(),
                "end_at": (start_at + timedelta(hours=1)).isoformat(),
                "participants_count": 2,
            },
            headers=headers,
        )
        ready = await client.get("/api/v1/health/ready")

    assert ai_response.status_code == 503
    assert ai_response.json()["error"]["code"] == "ai_unavailable"
    assert manual.status_code == 201, manual.text
    assert ready.status_code == 200
    assert await _booking_count(session_factory) == 1
