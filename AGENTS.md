# AiSpace agent instructions

## Architecture invariants

- PostgreSQL is the source of truth. Prevent overlap between confirmed bookings for one room with a PostgreSQL `btree_gist` GiST exclusion constraint.
- Booking intervals are `[start, end)`. Persist timezone-aware values as `TIMESTAMPTZ`; the configurable office timezone defaults to `Asia/Almaty`.
- Manual and AI booking both call the same `BookingService`. DeepSeek only maps text to a `BookingIntent`; it never writes data.
- Treat every LLM response as untrusted. Apply Pydantic validation and business validation, and request clarification instead of inventing critical values.
- Manual booking must work while DeepSeek is unavailable. Prefer explicit code and one deployable application over speculative abstractions.

## Repository structure

- `backend/`: FastAPI, domain services, SQLAlchemy, Alembic, and Python tests.
- `frontend/`: React/Vite client and component tests.
- `e2e/`: Playwright browser tests.
- `nginx/`, `compose.yaml`: local/runtime packaging and one-origin routing.
- `docs/`: requirements, architecture, decisions, and sequential Codex phase prompts.

## Required commands

- Local stack: `docker compose up --build`; validate with `docker compose config`.
- Backend: `cd backend && uv sync --frozen && uv run ruff format --check . && uv run ruff check . && uv run pyright && uv run pytest && uv build`.
- Frontend: `cd frontend && npm ci && npm run lint && npm run typecheck && npm test -- --run && npm run build`.
- E2E: `cd e2e && npm ci && npx playwright test`.

## Testing rules

- Add regression tests with each behavior change. Test domain rules at the lowest useful layer and API behavior at integration level.
- PostgreSQL-dependent tests use real PostgreSQL/Testcontainers, never SQLite. Mock DeepSeek in normal CI.
- Always cover interval boundaries, authorization, rollback, external failures, and the concurrent double-booking race.

## Security rules

- Never commit or log secrets, passwords, password hashes, JWTs, API keys, authorization headers, or full private meeting content.
- Hash passwords with Argon2, validate at trust boundaries, use least privilege, and keep credentials in environment variables.
- Review staged changes for secrets and unsafe defaults before every commit.

## Definition of done

- The phase scope is complete, documented, tested, and backward-compatible with these invariants.
- Formatting, lint, type checks, relevant tests, builds, and `git diff --check` pass; Docker is verified when affected.
- The diff is focused and reviewed, then committed with a logical Conventional Commit only after verification succeeds.

## Explicit non-goals

- No LangChain, LangGraph, microservices, Redis, Celery, Kafka, RabbitMQ, Kubernetes, Terraform, vector database, RAG, WebSockets, admin/RBAC system, or analytics platform without a concrete requirement.
- Do not duplicate backend business rules in the frontend or let an LLM calculate availability, authorize actions, or mutate persistence.
