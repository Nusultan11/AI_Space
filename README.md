# AiSpace

AiSpace is a production-minded meeting-room booking test project. Phase 05 adds safe DeepSeek-backed booking-intent previews to authentication, concurrency-safe booking, schedules, availability, and conflict alternatives.

## Problem

Employees need to arrange meetings reliably through either a normal form or natural-language input, without double-booking rooms.

## Product goals

- Correct manual booking, availability, cancellation, and useful conflict alternatives.
- Natural-language intent extraction with preview and explicit user confirmation.
- Database-enforced booking integrity, clear failure behavior, and a simple reviewable design.

## Planned features

Authentication, room schedules, manual and AI-assisted booking, booking previews, availability suggestions, cancellation history, health endpoints, and browser-level user flows.

## Tech stack

FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL, Alembic, React, TypeScript, Vite, MUI, TanStack Query, React Hook Form, Zod, Playwright, Docker Compose, Nginx, and DeepSeek.

## Quick start

With Docker Desktop running:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:8080`. Nginx serves the React shell and proxies `/api` to FastAPI. The stack waits for PostgreSQL health, applies Alembic migrations once, then starts the backend and frontend.

Useful checks:

```powershell
Invoke-RestMethod http://localhost:8080/api/v1/health/live
Invoke-RestMethod http://localhost:8080/api/v1/health/ready
docker compose ps
```

The runtime seeds the three demo rooms idempotently after migrations. Register at `POST /api/v1/auth/register`, obtain a Bearer token from `POST /api/v1/auth/login`, then use `/api/v1/users/me`, `/api/v1/rooms`, `/api/v1/bookings`, `/api/v1/rooms/{id}/schedule?date=YYYY-MM-DD`, `/api/v1/availability?start_at=...&end_at=...`, and `POST /api/v1/ai/booking-intent`. Continue with `docs/codex/06-frontend.md` only after Phase 05 verification passes.

## Architecture and data model

The browser uses the React frontend, which calls `/api/v1` on FastAPI. Domain services persist users, rooms, and bookings through SQLAlchemy to PostgreSQL. See `docs/ARCHITECTURE.md` for boundaries and the planned schema.

## Booking conflict protection

Intervals are half-open (`[start, end)`). A PostgreSQL GiST exclusion constraint is the final guard against overlapping confirmed bookings in the same room, including concurrent requests.

Conflict responses first suggest up to three active, sufficiently large rooms free at the requested time. If none qualify, they provide up to three exact-duration slots for the requested room, searched forward in 15-minute increments for at most seven days. Room schedules represent one local calendar day and expose only occupied start/end times.

## Natural-language booking and AI reliability

DeepSeek may only produce a validated `BookingIntent` preview. It cannot check availability or write to the database. Missing or ambiguous critical values produce a clarification preview; confirmation uses the normal booking endpoint. Configure `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, and `DEEPSEEK_TIMEOUT_SECONDS` for live parsing. Missing configuration or provider failure affects only the AI endpoint, not readiness or manual booking. Normal tests use no live key or provider call.

## Timezone strategy

The office timezone is configurable and defaults to `Asia/Almaty`. API boundaries require timezone-aware datetimes and PostgreSQL stores booking times as `TIMESTAMPTZ`.

## Security and testing

Passwords use Argon2; JWT/API secrets remain in environment variables and sensitive values are excluded from logs. Critical tests use real PostgreSQL and cover authorization, time boundaries, concurrency, DeepSeek failures, and the two primary Playwright flows.

## Assumptions, decisions, and trade-offs

`docs/DECISIONS.md` separates confirmed decisions from open product questions. The main trade-off is deliberate simplicity: one application and explicit services instead of infrastructure or framework layers without demonstrated need.

## Known limitations

Phase 05 has no booking frontend, recurring meetings, notifications, or business-hours policy. Live DeepSeek connectivity is configuration-dependent and was not required for normal verification. Authentication uses short-lived access tokens only; refresh tokens, OAuth, SSO, and RBAC are out of scope.

## Future improvements

Only after the required system is correct: measure booking success, conflicts, AI clarification/conversion, cancellation, and room utilization. Do not build an analytics platform for this assignment.
