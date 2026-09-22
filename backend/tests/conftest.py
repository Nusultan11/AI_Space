from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from testcontainers.community.postgres import PostgresContainer

from app.db.session import create_database_engine, create_session_factory

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://aispace:change-me-local-only@localhost:5432/aispace",
)
os.environ.setdefault("JWT_SECRET", "test-only-secret-with-sufficient-length")

BACKEND_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PostgresTestDatabase:
    async_url: str
    sync_url: str


@pytest.fixture(scope="session")
def postgres_database() -> Iterator[PostgresTestDatabase]:
    with PostgresContainer(
        "postgres:17-alpine",
        username="aispace_test",
        password="aispace_test",
        dbname="aispace_test",
    ) as postgres:
        container_url = postgres.get_connection_url()
        sync_url = re.sub(
            r"^postgresql(?:\+psycopg2)?://",
            "postgresql://",
            container_url,
        )
        async_url = re.sub(
            r"^postgresql(?:\+psycopg2)?://",
            "postgresql+asyncpg://",
            container_url,
        )
        yield PostgresTestDatabase(async_url=async_url, sync_url=sync_url)


@pytest.fixture(scope="session")
def migrated_database(postgres_database: PostgresTestDatabase) -> PostgresTestDatabase:
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
    if result.returncode != 0:
        pytest.fail(result.stderr)
    return postgres_database


@pytest_asyncio.fixture
async def database_engine(
    migrated_database: PostgresTestDatabase,
) -> AsyncIterator[AsyncEngine]:
    engine = create_database_engine(migrated_database.async_url)
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE TABLE users, rooms CASCADE"))
    yield engine
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE TABLE users, rooms CASCADE"))
    await engine.dispose()


@pytest.fixture
def session_factory(
    database_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(database_engine)
