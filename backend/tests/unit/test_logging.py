from __future__ import annotations

from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.logging import REDACTED, redact_sensitive
from app.core.request_id import REQUEST_ID_HEADER
from app.main import create_app


def test_logging_redacts_sensitive_values_recursively() -> None:
    event = {
        "event": "request_received",
        "email": "person@example.com",
        "password": "not-for-logs",
        "headers": {"Authorization": "Bearer token", "x-safe": "visible"},
        "payload": [{"api-key": "secret"}, {"meeting_content": "private"}],
    }

    redacted = redact_sensitive(None, "info", event)

    assert redacted["email"] == "person@example.com"
    assert redacted["password"] == REDACTED
    assert redacted["headers"] == {"Authorization": REDACTED, "x-safe": "visible"}
    assert redacted["payload"] == [{"api-key": REDACTED}, {"meeting_content": REDACTED}]


@pytest.mark.asyncio
async def test_request_id_is_propagated_or_replaced() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql+asyncpg://aispace:test@localhost:5432/unused",
    )
    app = create_app(settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        propagated = await client.get(
            "/api/v1/health/live",
            headers={REQUEST_ID_HEADER: "review-123"},
        )
        generated = await client.get(
            "/api/v1/health/live",
            headers={REQUEST_ID_HEADER: "invalid request id"},
        )
    await app.state.database_engine.dispose()

    assert propagated.headers[REQUEST_ID_HEADER] == "review-123"
    assert UUID(generated.headers[REQUEST_ID_HEADER])
