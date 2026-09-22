from __future__ import annotations

from typing import Protocol

import psycopg
import pytest


class PostgresTestDatabase(Protocol):
    async_url: str
    sync_url: str


@pytest.mark.integration
def test_alembic_upgrade_on_clean_postgresql(
    migrated_database: PostgresTestDatabase,
) -> None:
    with (
        psycopg.connect(migrated_database.sync_url) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT version_num FROM alembic_version")
        assert cursor.fetchone() == ("0002_auth_rooms",)
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        )
        assert cursor.fetchall() == [("alembic_version",), ("rooms",), ("users",)]
