from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Protocol

import psycopg
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]


class PostgresTestDatabase(Protocol):
    async_url: str
    sync_url: str


@pytest.mark.integration
def test_alembic_upgrade_on_clean_postgresql(
    postgres_database: PostgresTestDatabase,
) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = postgres_database.async_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    with (
        psycopg.connect(postgres_database.sync_url) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT version_num FROM alembic_version")
        assert cursor.fetchone() == ("0001_foundation",)
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        )
        assert cursor.fetchall() == [("alembic_version",)]
