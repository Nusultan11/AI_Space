from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

DATABASE_URL = "postgresql+asyncpg://aispace:test@localhost:5432/aispace"


def test_settings_use_foundation_defaults() -> None:
    settings = Settings(database_url=DATABASE_URL)

    assert settings.app_env == "development"
    assert settings.app_port == 8000
    assert settings.app_log_level == "INFO"
    assert settings.office_timezone == "Asia/Almaty"


def test_settings_require_async_postgresql_url() -> None:
    with pytest.raises(ValidationError, match=r"postgresql\+asyncpg"):
        Settings(database_url="sqlite:///local.db")


def test_settings_reject_unknown_timezone() -> None:
    with pytest.raises(ValidationError, match="Unknown OFFICE_TIMEZONE"):
        Settings(database_url=DATABASE_URL, office_timezone="Mars/Olympus")


def test_production_rejects_placeholder_database_credentials() -> None:
    with pytest.raises(ValidationError, match="placeholder credentials"):
        Settings(
            app_env="production",
            database_url=(
                "postgresql+asyncpg://aispace:change-me-local-only@postgres:5432/aispace"
            ),
        )
