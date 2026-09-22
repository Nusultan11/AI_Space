# AiSpace architecture blueprint

## System shape

```text
Browser
  → Nginx (single origin; static frontend and /api proxy)
    → React + TypeScript frontend
    → FastAPI /api/v1
      → authentication and request validation
      → BookingService / AvailabilityService / BookingIntentParser
      → SQLAlchemy 2 + asyncpg
        → PostgreSQL

DeepSeek API ← DeepSeekBookingIntentParser (intent extraction only)
```

AiSpace is one deployable application, not a microservice system. PostgreSQL is the source of truth. The frontend owns interaction state; the backend owns all domain and authorization rules.

## Monorepo boundaries

```text
backend/              Python package, migrations, unit/integration tests
frontend/             React application and component tests
e2e/                  Playwright configuration and browser journeys
nginx/                production SPA/proxy configuration
.github/workflows/    CI
.codex/               project-local Codex configuration
docs/                 requirements, architecture, decisions, phase prompts
compose.yaml          local and review runtime
```

The intended backend layers are HTTP routers/dependencies → application services → repositories/models/integrations. Avoid generic base classes and abstractions until two concrete implementations need them. The parser protocol is justified because production and fake implementations are required.

## Data model

### `users`

UUID primary key; normalized unique email; name; `password_hash`; `is_active`; timezone-aware created/updated timestamps.

### `rooms`

UUID primary key; unique name; capacity with `capacity > 0`; optional description; `is_active`; timezone-aware created/updated timestamps.

### `bookings`

UUID primary key; indexed foreign keys to room and user; title; `start_at`/`end_at` as `TIMESTAMPTZ`; optional positive `participants_count`; status enum (`confirmed`, `cancelled`); created/updated timestamps; nullable `cancelled_at`; `end_at > start_at` check.

Enable `btree_gist` and add a GiST exclusion constraint equivalent to:

```sql
EXCLUDE USING gist (
  room_id WITH =,
  tstzrange(start_at, end_at, '[)') WITH &&
) WHERE (status = 'confirmed')
```

This constraint—not an application query—settles concurrent races. Translate its integrity violation to the standard conflict response after rollback.

## Time model

- API date-times must include an offset. Internally compare aware values and persist instants with `TIMESTAMPTZ`.
- `OFFICE_TIMEZONE` controls natural-language interpretation and display context; default `Asia/Almaty`.
- Half-open intervals allow an event ending at 15:00 and another starting at 15:00.
- Python uses `zoneinfo`; calculation and comparison are deterministic and never delegated to the LLM.

## Core services

### `BookingService`

The only booking mutation path for both manual and AI-confirmed flows. It validates room/activity, interval, past time, participant count/capacity where specified, ownership for cancellation, and transaction behavior. It performs a friendly conflict pre-check, persists in a transaction, handles the database exclusion violation, rolls back, and returns a 409 conflict with alternatives when available.

### `AvailabilityService`

Queries schedules and free rooms using `[start, end)` rules and supplies deterministic conflict alternatives. A schedule is one `OFFICE_TIMEZONE` calendar day. Free rooms use one correlated `NOT EXISTS` query; confirmed bookings for nearest-slot search are loaded once for a bounded seven-day window and scanned in memory at 15-minute increments. Alternatives prefer up to three best-fit rooms at the requested time, then up to three exact-duration slots for the requested room. The service does not mutate bookings or commit transactions.

### `BookingIntentParser`

Receives only user text, local current time, timezone, and the active room catalog. `DeepSeekBookingIntentParser` requests JSON through the OpenAI-compatible SDK; `FakeBookingIntentParser` makes tests deterministic. Provider content is checked for emptiness, decoded, Pydantic-validated, and then independently checked against the exact catalog, timezone, interval, past-time, and capacity rules by `AIBookingService`. Parser output is a preview and neither parser has persistence capability.

## API and errors

FastAPI exposes `/api/v1` endpoints listed in `docs/TASK.md`. JWT Bearer dependencies provide the current user. Application errors and FastAPI/Pydantic request-validation failures use one error shape, for example `{"error":{"code":"booking_conflict","message":"…","details":{…},"request_id":"…"}}`. Validation details expose only safe field location, message, and type metadata; raw submitted values are never echoed.

Schedules expose occupied start/end instants without other users' titles or identities. Booking conflicts use one typed details shape containing `alternative_rooms` and `alternative_slots`; one list is populated according to the room-first priority. The database-race path rolls back the failed transaction before querying these alternatives.

Liveness does not depend on PostgreSQL or DeepSeek. Readiness checks PostgreSQL and other required local dependencies; DeepSeek is optional because manual booking must remain healthy.

## AI trust boundary

DeepSeek receives only the minimum context needed. Its structured JSON is parsed, schema-validated, cross-checked against the supplied room catalog, and business-validated. Ambiguous or missing room, start, end/duration, or title returns a normalized clarification preview instead of invented values. The flow is text → parser → validated preview → explicit user confirmation → normal `POST /bookings`; the AI endpoint never checks availability or writes data.

Timeouts map to `ai_timeout`/504; missing configuration, connection failures, rate limits, and provider failures map to `ai_unavailable`/503; empty, malformed, schema-invalid, or impossible output maps to `ai_invalid_response`/502. Provider details and raw content are not returned or logged. DeepSeek remains outside readiness, and normal CI uses fakes/mocks rather than a live API.

## Runtime

Docker Compose will orchestrate PostgreSQL health, one-shot migrations, one-shot idempotent seed, backend, and Nginx-served frontend. Service dependency conditions prevent startup races. Configuration comes from environment variables documented in `.env.example`; production secrets are never defaults.

## Verification strategy

- Pure unit tests for validation and deterministic service decisions.
- FastAPI/API tests for contracts and authorization.
- Real PostgreSQL integration tests for migrations, range logic, constraint translation, and concurrency.
- Mocked/fake DeepSeek contract and failure tests in normal CI.
- Frontend component tests for state and validation; Playwright for the two critical user journeys.
- CI checks format, lint, types, tests, builds, migrations, Docker images, and E2E where practical.
- GitHub Actions separates backend, frontend, and clean Compose runtime/E2E gates. The runtime gate starts from removed volumes, verifies public health routes and one-shot services, replays migrations and seed data, proves the three demo rooms remain unique, runs without a DeepSeek key, prints diagnostics on failure, and always removes its volumes.

## Observability and security

Middleware assigns/propagates request IDs and emits structured logs. Redact passwords, hashes, tokens, API keys, authorization headers, and unnecessary meeting text. Apply Argon2 password hashing, short explicit JWT configuration, input validation at boundaries, and least-privilege database/runtime configuration.
