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

## Completion report

After every meaningful implementation task or project phase—not after every tiny edit—provide a compact, result-oriented report, normally 5–12 lines, using exactly this structure:

1. **Completed:** State what was created, changed, fixed, or implemented and the concrete result achieved. Mention important affected areas or files when useful, and include the commit hash if a required commit was created.
2. **Verification:** List only checks actually executed and their real results, including relevant tests, lint, type checks, builds, migrations, Docker/Compose validation, E2E, Git diff, or Git status.
3. **Issues / limitations:** State remaining failures, blockers, environment problems, assumptions, deferred items, and skipped or unavailable checks. Write `None` when there are none.
4. **Current state:** Use exactly one of `DONE`, `PARTIAL`, or `BLOCKED`, with a brief reason. `DONE` requires all required work and verification to pass; use `PARTIAL` when work is implemented but required verification or scope remains, and `BLOCKED` when progress requires an unavailable external dependency or user action. Clearly distinguish implemented work from verified work.
5. **Next action:** State the exact next phase, task, or prompt to execute; do not begin it automatically.

Describe outcomes rather than every command. Avoid vague phrases such as “updated code” or “made improvements,” and omit raw logs unless they explain a failure. Explicitly report failed, skipped, or environment-blocked verification; never claim an unexecuted check passed or mark the task `DONE` while required verification is failing or missing.

## Explicit non-goals

- No LangChain, LangGraph, microservices, Redis, Celery, Kafka, RabbitMQ, Kubernetes, Terraform, vector database, RAG, WebSockets, admin/RBAC system, or analytics platform without a concrete requirement.
- Do not duplicate backend business rules in the frontend or let an LLM calculate availability, authorize actions, or mutate persistence.
