# AiSpace

AiSpace is a production-minded meeting-room booking test project. This repository is currently bootstrapped for sequential Codex-driven implementation; product code is intentionally deferred to the phase prompts in `docs/codex/`.

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

Bootstrap currently validates with:

```sh
docker compose config
```

Implement phases in order, beginning with `docs/codex/01-foundation.md`. The completed application must start with:

```sh
docker compose up --build
```

## Architecture and data model

The browser uses the React frontend, which calls `/api/v1` on FastAPI. Domain services persist users, rooms, and bookings through SQLAlchemy to PostgreSQL. See `docs/ARCHITECTURE.md` for boundaries and the planned schema.

## Booking conflict protection

Intervals are half-open (`[start, end)`). A PostgreSQL GiST exclusion constraint is the final guard against overlapping confirmed bookings in the same room, including concurrent requests.

## Natural-language booking and AI reliability

DeepSeek may only produce a validated `BookingIntent` preview. It cannot write to the database. Missing or ambiguous critical values cause clarification, and manual booking remains available during AI failures.

## Timezone strategy

The office timezone is configurable and defaults to `Asia/Almaty`. API boundaries require timezone-aware datetimes and PostgreSQL stores booking times as `TIMESTAMPTZ`.

## Security and testing

Passwords use Argon2; JWT/API secrets remain in environment variables and sensitive values are excluded from logs. Critical tests use real PostgreSQL and cover authorization, time boundaries, concurrency, DeepSeek failures, and the two primary Playwright flows.

## Assumptions, decisions, and trade-offs

`docs/DECISIONS.md` separates confirmed decisions from open product questions. The main trade-off is deliberate simplicity: one application and explicit services instead of infrastructure or framework layers without demonstrated need.

## Known limitations

This bootstrap contains documentation and infrastructure boundaries only. Application dependencies, source code, migrations, UI, tests, CI, and production Nginx configuration are delivered by phases 01–08.

## Future improvements

Only after the required system is correct: measure booking success, conflicts, AI clarification/conversion, cancellation, and room utilization. Do not build an analytics platform for this assignment.
