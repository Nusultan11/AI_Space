# AiSpace

AiSpace is a single-deployment meeting-room booking application. It supports authenticated manual booking, deterministic availability search, and an optional DeepSeek-assisted flow that converts natural language into a reviewable booking draft. PostgreSQL remains the source of truth for every confirmed booking.

## Product outcome

- Register and sign in with email and password.
- Browse rooms, schedules, availability, and personal bookings.
- Create and cancel bookings through one shared backend service.
- Prevent overlapping confirmed bookings at the PostgreSQL constraint layer.
- Turn natural-language requests into validated booking previews without allowing the LLM to write data.
- Keep manual booking fully operational when DeepSeek is unavailable.

## Stack

- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, asyncpg, Alembic, PostgreSQL, PyJWT, Argon2, pytest, Ruff, and Pyright.
- Frontend: React, TypeScript, Vite, MUI, TanStack Query, React Hook Form, Zod, and Vitest.
- Runtime: Docker Compose and Nginx, with one public origin at `http://localhost:8080`.
- Browser tests: Playwright.

## Clean startup

Docker Desktop must be running with the Linux engine available.

```bash
docker compose down -v --remove-orphans
docker compose up --build -d
docker compose ps -a
```

Open [http://localhost:8080](http://localhost:8080). The public health endpoints are:

- `http://localhost:8080/api/v1/health/live`
- `http://localhost:8080/api/v1/health/ready`

The migration and seed services should exit successfully; PostgreSQL, backend, and frontend should remain healthy or running. Stop and remove the stack with:

```bash
docker compose down -v --remove-orphans
```

## Configuration

Copy `.env.example` to `.env` only when local overrides are needed. Never commit `.env` or credentials. Development defaults are provided by Compose; production configuration rejects placeholder database and JWT secrets.

`DEEPSEEK_API_KEY` is optional. With no key, manual booking and all non-AI functionality remain available, while the AI intent endpoint returns its documented unavailable response. Normal tests and CI do not require a live DeepSeek key.

Local Compose deliberately uses the same demo PostgreSQL role for migrations and application runtime to keep review startup simple. A production deployment should provision separate migration and least-privilege runtime roles rather than reuse these local credentials.

## Architecture boundaries

- The FastAPI application is one deployable backend; PostgreSQL owns persistent state.
- `BookingService` is the only booking mutation path. Both manual and AI-assisted confirmation use `POST /api/v1/bookings`.
- DeepSeek only produces an untrusted `BookingIntent`. Pydantic and business validation run before any preview can be confirmed.
- The frontend uses TanStack Query for server state. Authentication state is stored in `sessionStorage`; it is not persisted indefinitely.
- Nginx serves the SPA and proxies `/api/` to the backend under the same origin.

## Data, time, availability, and conflicts

The persistent core data model contains users, rooms, and bookings. A room schedule is a derived, read-only view of confirmed bookings that overlap one selected local calendar day; that day's boundaries are interpreted using `OFFICE_TIMEZONE`. Booking timestamps are stored as timezone-aware `TIMESTAMPTZ` values. Intervals use half-open semantics, `[start, end)`, so one booking may start exactly when another ends. The office timezone defaults to `Asia/Almaty` and is configurable.

Availability and derived schedule views are computed deterministically from active rooms and confirmed bookings. PostgreSQL is the final concurrency authority: a `btree_gist` exclusion constraint prevents two confirmed bookings for one room from overlapping, including concurrent requests. Conflict responses first suggest active rooms with enough capacity that are free for the requested interval; when none qualify, they suggest exact-duration slots for the requested room within the bounded search window. These alternatives are advisory—the database constraint still decides whether the retried booking succeeds.

## DeepSeek trust boundary

The AI endpoint accepts natural language, asks DeepSeek for structured intent, validates the response, and returns either a preview or a clarification/error. DeepSeek does not calculate availability, authorize users, or write bookings. Provider timeouts, malformed output, unavailable credentials, and unsafe values are isolated from manual booking. Live provider behavior is not claimed by the automated suite because CI uses deterministic mocks and no API key.

## Browser flows and accessibility

The SPA provides sign-in/registration, room and availability views, manual booking, AI-assisted preview, booking history, and cancellation. The frontend offers the cancel action for upcoming confirmed bookings; the backend enforces ownership and already-cancelled state without adding a separate rule that forbids cancelling past bookings. Forms use labeled controls, keyboard-operable MUI components, visible validation feedback, and status/error messaging. Browser tests exercise the public Nginx route and real booking APIs; only the DeepSeek intent call is mocked in the AI flow.

## API surface

The versioned API under `/api/v1` includes:

- `/auth/register`, `/auth/login`, and `/users/me`
- `/rooms` and room schedule endpoints
- `/availability`
- `/bookings` and booking cancellation
- `/ai/booking-intent`
- `/health/live` and `/health/ready`

Application errors and FastAPI/Pydantic validation failures use the same envelope with a stable code, safe message, request ID, and optional details. Validation details expose only field location, message, and type; submitted secret or private values are not echoed.

## Security and observability

- Passwords are hashed with Argon2; secrets and tokens come from environment variables.
- Request IDs are accepted or generated, returned in response headers, and attached to structured JSON logs.
- Sensitive log fields such as passwords, tokens, authorization headers, API keys, and meeting content are redacted recursively.
- Repository and Docker ignore rules exclude credentials, caches, build output, reports, and local runtime data.

## Local quality commands

Backend:

```bash
cd backend
uv lock --check
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv build
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

Runtime and E2E:

```bash
docker compose config
docker compose down -v --remove-orphans
docker compose up --build -d
cd e2e
npm ci
npx playwright test
```

PostgreSQL-dependent backend tests use Testcontainers and require a working Docker daemon. They never substitute SQLite.

## Test strategy and CI

Unit tests cover domain and trust-boundary behavior, integration tests exercise real PostgreSQL, frontend tests cover components and client behavior, and Playwright covers complete public-stack journeys. Important coverage includes interval boundaries, authorization, rollback, external-provider failures, cancellation, and the concurrent double-booking race.

GitHub Actions runs three gates: the complete backend quality suite, the complete frontend quality suite, and a clean Compose runtime plus Playwright gate. The runtime gate verifies migrations, health routes, idempotent seed replay, and exactly three demo rooms without a DeepSeek key. Failed runtime jobs retain diagnostic logs in the job output and always remove the Compose volumes.

## Assumptions, tradeoffs, and limitations

- There is no weekly office-hours or business-hours model; a business-hours policy is intentionally not implemented. Recurring meetings are outside the current scope.
- AI suggestions require manual review and confirmation; live DeepSeek connectivity is deployment-specific and is not verified in CI.
- The frontend production build currently emits Vite's informational large-chunk warning (approximately 632 kB); the build still succeeds and bundle splitting is deferred because it is not a Phase 07 correctness failure.
- The repository intentionally avoids microservices, queues, Redis, Kubernetes, LangChain, and other infrastructure without a concrete requirement.

## Future improvements

- Resolve the documented open choices for booking-list ordering and production deployment/TLS when product and target-environment requirements are available.
- Measure real frontend loading performance before deciding whether the current production bundle needs code splitting or other optimization.
