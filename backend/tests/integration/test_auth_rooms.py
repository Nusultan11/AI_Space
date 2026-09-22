from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.security import verify_password
from app.db.seed import seed_rooms
from app.main import create_app
from app.models.room import Room
from app.models.user import User

JWT_SECRET = "integration-test-secret-with-sufficient-length"


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


async def register(client: AsyncClient, *, email: str = "person@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Example User", "password": "correct-password"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def login(client: AsyncClient, *, email: str = "person@example.com") -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-password"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_registration_normalizes_email_and_stores_only_hash(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    payload = await register(client, email="  Person@Example.COM ")

    assert payload["email"] == "person@example.com"
    assert "password" not in payload
    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.email == "person@example.com"))
        assert user is not None
        assert user.password_hash != "correct-password"
        assert verify_password("correct-password", user.password_hash)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_duplicate_registration_uses_error_envelope(client: AsyncClient) -> None:
    await register(client)

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "PERSON@example.com",
            "name": "Other Name",
            "password": "another-password",
        },
        headers={"X-Request-ID": "duplicate-registration"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "email_already_registered",
            "message": "An account with this email already exists.",
            "request_id": "duplicate-registration",
        }
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_and_current_user_contract(client: AsyncClient) -> None:
    registered = await register(client)
    token = await login(client, email="PERSON@example.com")

    response = await client.get("/api/v1/users/me", headers=bearer(token))
    unauthenticated = await client.get("/api/v1/users/me")

    assert response.status_code == 200
    assert response.json()["id"] == registered["id"]
    assert response.json()["email"] == "person@example.com"
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "not_authenticated"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_credentials_do_not_disclose_account_state(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register(client)
    token = await login(client)
    wrong_password = await client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "incorrect-password"},
    )
    missing_user = await client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "incorrect-password"},
    )
    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.email == "person@example.com"))
        assert user is not None
        user.is_active = False
        await session.commit()
    inactive_user = await client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "correct-password"},
    )
    inactive_token = await client.get("/api/v1/users/me", headers=bearer(token))

    expected = {"code": "invalid_credentials", "message": "Invalid email or password."}
    for response in (wrong_password, missing_user, inactive_user):
        assert response.status_code == 401
        error = response.json()["error"]
        assert {"code": error["code"], "message": error["message"]} == expected
    assert inactive_token.status_code == 401
    assert inactive_token.json()["error"]["code"] == "not_authenticated"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_room_catalog_exposes_only_active_rooms(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register(client)
    token = await login(client)
    async with session_factory() as session:
        await seed_rooms(session)
        inactive = Room(name="Inactive room", capacity=2, is_active=False)
        session.add(inactive)
        await session.commit()
        await session.refresh(inactive)

    listed = await client.get("/api/v1/rooms", headers=bearer(token))
    detail = await client.get(
        f"/api/v1/rooms/{listed.json()[0]['id']}",
        headers=bearer(token),
    )
    inactive_detail = await client.get(
        f"/api/v1/rooms/{inactive.id}",
        headers=bearer(token),
    )
    missing_detail = await client.get(
        f"/api/v1/rooms/{uuid4()}",
        headers=bearer(token),
    )
    unauthenticated = await client.get("/api/v1/rooms")

    assert listed.status_code == 200
    assert {room["name"] for room in listed.json()} == {
        "Большая переговорная",
        "Средняя переговорная",
        "Малая переговорная",
    }
    assert detail.status_code == 200
    assert inactive_detail.status_code == 404
    assert inactive_detail.json()["error"]["code"] == "room_not_found"
    assert missing_detail.status_code == 404
    assert missing_detail.json()["error"]["code"] == "room_not_found"
    assert unauthenticated.status_code == 401
