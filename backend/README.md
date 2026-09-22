# Backend workspace

The Phase 01 backend provides typed environment settings, async SQLAlchemy infrastructure, an empty Alembic baseline, structured logging, request IDs, and health endpoints. It intentionally has no product schema or domain services.

```powershell
uv sync --frozen
$env:DATABASE_URL = "postgresql+asyncpg://aispace:change-me-local-only@localhost:5432/aispace"
uv run uvicorn app.main:app --reload
```

Quality gate:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv build
```

`GET /api/v1/health/live` checks only the process. `GET /api/v1/health/ready` executes `SELECT 1` against PostgreSQL. Integration tests require a running Docker daemon because they use Testcontainers with real PostgreSQL.
