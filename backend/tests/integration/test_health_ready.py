from __future__ import annotations

from typing import Protocol

import pytest
from httpx2 import ASGITransport, AsyncClient

from app.core.config import Settings
from app.db.session import create_database_engine
from app.main import create_app


class PostgresTestDatabase(Protocol):
    async_url: str
    sync_url: str


def _settings(database_url: str) -> Settings:
    return Settings(app_env="test", database_url=database_url)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_readiness_succeeds_with_real_postgresql(
    postgres_database: PostgresTestDatabase,
) -> None:
    engine = create_database_engine(postgres_database.async_url)
    app = create_app(_settings(postgres_database.async_url), engine)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health/ready")
    await engine.dispose()

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_readiness_failure_uses_shared_error_envelope() -> None:
    app = create_app(_settings("postgresql+asyncpg://aispace:test@localhost:5432/unavailable"))

    async def unavailable() -> None:
        raise OSError("database details must not leak")

    app.state.database_healthcheck = unavailable
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/health/ready",
            headers={"X-Request-ID": "readiness-test"},
        )
    await app.state.database_engine.dispose()

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "database_unavailable",
            "message": "Database is unavailable.",
            "request_id": "readiness-test",
        }
    }
    assert response.headers["X-Request-ID"] == "readiness-test"
