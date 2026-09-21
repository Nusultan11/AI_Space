# AiSpace product requirements

This document preserves the supplied technical assignment as the source of product requirements. `docs/ARCHITECTURE.md` is the implementation blueprint. Unspecified behavior is listed as open in `docs/DECISIONS.md`; it must not be guessed silently.

## Product outcome

Build a simple, production-minded meeting-room booking application that is correct, explainable, easy to review, and starts on a clean Docker machine with `docker compose up --build`.

Users must be able to register, sign in, browse rooms and schedules, check availability, create manual bookings, view and cancel their own bookings, and use natural language to prepare a booking preview. The AI flow requires explicit confirmation through the normal booking API.

## Required technology

- Backend: Python 3.12+, uv, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2, asyncpg, Alembic, PostgreSQL, PyJWT, pwdlib/Argon2, and HTTPX or an OpenAI-compatible DeepSeek client.
- Backend quality: pytest, pytest-asyncio, Testcontainers, Ruff, and Pyright.
- Frontend: React, TypeScript, Vite, MUI, TanStack Query, React Hook Form, and Zod.
- E2E and runtime: Playwright, Docker Compose, Nginx, and GitHub Actions.
- AI provider: DeepSeek API, isolated behind the parser interface described below.

## Domain requirements

### Users

- UUID identifier, normalized unique email, name, Argon2 password hash, active flag, and created/updated timestamps.
- JWT Bearer authentication supports registration, login, and current-user lookup.
- An authenticated user may cancel only their own booking. No admin/RBAC system is required.

### Rooms

- UUID identifier, unique name, positive capacity, description, active flag, and timestamps.
- Idempotently seed: Большая переговорная (12), Средняя переговорная (6), Малая переговорная (4).

### Bookings

- UUID identifier, room/user references, title, timezone-aware start/end, optional participant count, `confirmed`/`cancelled` status, timestamps, and optional cancellation time.
- Require `end_at > start_at`; reject past bookings and invalid/missing rooms.
- Confirmed bookings for the same room must not overlap. Use `[start, end)` semantics, so adjacent bookings are allowed.
- Preserve cancellation history; cancelled bookings no longer block availability.
- Friendly application pre-checks improve UX, but a PostgreSQL constraint is the final concurrency guarantee.

## Availability and conflicts

Provide room schedule, rooms free in an interval, nearest free slot, and alternatives. On conflict, prefer:

1. a suitable alternative room at the requested time;
2. the nearest free slot for the requested room.

Return a consistent error envelope with machine-readable codes and HTTP 409 for booking conflicts.

## API surface

All product endpoints use `/api/v1`:

- `POST /auth/register`, `POST /auth/login`, `GET /users/me`
- `GET /rooms`, `GET /rooms/{id}`, `GET /rooms/{id}/schedule`
- `GET /availability`
- `GET /bookings`, `POST /bookings`, `GET /bookings/{id}`, `POST /bookings/{id}/cancel`
- `POST /ai/booking-intent`
- `GET /health/live`, `GET /health/ready`

## DeepSeek requirements

- A `BookingIntentParser` abstraction has real DeepSeek and fake implementations.
- Input includes user text, current local datetime, configured timezone, and current room catalog.
- Output is a Pydantic-validated `BookingIntent` containing room reference/ID, start/end, title, optional participant count, clarification flag, missing fields, and clarification message as appropriate.
- Use structured JSON. Validate schema and business rules. Room IDs must come from the supplied catalog.
- Never invent missing or ambiguous critical date/time/room values; request clarification.
- Handle timeouts, 429, 5xx, invalid JSON, empty output, and schema violations.
- Parsing creates a preview only: text → parser → validated intent → preview → confirmation → normal `POST /bookings`.
- DeepSeek never writes to persistence, and its failure never disables manual booking.

## Frontend requirements

Provide a clean functional interface for registration/login, room list and schedule, manual booking, natural-language parsing states, preview/confirm/edit, conflict alternatives, the current user's bookings, cancellation, and loading/empty/error states. Do not duplicate backend business rules.

## Runtime and operations

- One Docker Compose command starts PostgreSQL, migrations, idempotent seed, backend, and frontend/Nginx.
- PostgreSQL has a healthcheck; migrations and seed execute safely; Nginx serves the frontend and proxies `/api` to FastAPI so users use one URL.
- `.env.example` enumerates configuration without real secrets.
- Add structured logs and request IDs. Never log credentials, authorization headers, tokens, API keys, or unnecessary full meeting content.
- Liveness checks process health; readiness checks required dependencies.

## Verification requirements

- Backend unit tests cover authentication, booking rules, availability, and parser behavior.
- Integration tests use real PostgreSQL/Testcontainers, not SQLite.
- Boundary tests prove adjacent intervals succeed; overlaps and enclosing intervals fail; equal times in different rooms succeed; cancelled bookings do not block.
- A concurrent same-room/same-time test proves one request succeeds, one conflicts, and exactly one confirmed row remains.
- DeepSeek tests use a fake/mock in normal CI and cover valid JSON, ambiguity, missing values, invalid JSON/schema, timeout, 429, 5xx, and empty output.
- Playwright covers manual booking plus conflict, and natural-language preview plus confirmation.
- CI runs backend formatting/lint/type/tests, frontend lint/type/tests/build, PostgreSQL integration tests, practical E2E, and Docker build.

## Delivery requirements

- Document problem, goals, features, stack, startup, architecture, schema, API, overlap protection, AI flow/reliability, timezone, security, tests, assumptions, decisions, trade-offs, limitations, and future improvements.
- Work through `docs/codex/01-foundation.md` to `08-final-audit.md` in order.
- Each phase ends with relevant verification, documentation updates, diff/secret review, and a logical Conventional Commit.
