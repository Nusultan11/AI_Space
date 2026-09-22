from __future__ import annotations

import pytest
from httpx2 import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


@pytest.mark.asyncio
async def test_liveness_does_not_touch_database() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql+asyncpg://aispace:test@localhost:5432/unused",
    )
    app = create_app(settings)
    called = False

    async def fail_if_called() -> None:
        nonlocal called
        called = True
        raise AssertionError("liveness must not call PostgreSQL")

    app.state.database_healthcheck = fail_if_called
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health/live")
    await app.state.database_engine.dispose()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert called is False
