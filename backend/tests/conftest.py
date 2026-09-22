from __future__ import annotations

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from testcontainers.community.postgres import PostgresContainer

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://aispace:change-me-local-only@localhost:5432/aispace",
)


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
