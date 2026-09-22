from __future__ import annotations

import pytest
from httpx2 import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


@pytest.mark.asyncio
async def test_request_validation_uses_safe_shared_error_envelope() -> None:
    app = create_app(
        Settings(
            app_env="test",
            database_url="postgresql+asyncpg://aispace:test@localhost:5432/unused",
        )
    )
    submitted_password = "private-password-" * 10
    submitted_email = "private-invalid-email"
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/auth/register",
            headers={"X-Request-ID": "validation-review-123"},
            json={
                "email": submitted_email,
                "name": "Reviewer",
                "password": submitted_password,
            },
        )
    await app.state.database_engine.dispose()

    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == "validation-review-123"
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "The request contains invalid values."
    assert payload["error"]["request_id"] == "validation-review-123"
    assert payload["error"]["details"]["errors"]
    assert all(
        set(error) == {"location", "message", "type"}
        for error in payload["error"]["details"]["errors"]
    )
    rendered = response.text
    assert submitted_password not in rendered
    assert submitted_email not in rendered
