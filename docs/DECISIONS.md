# AiSpace decisions

This log separates binding architecture decisions from product details that the assignment did not specify. Open items must be resolved explicitly during the relevant phase and documented here.

## ADR-001: PostgreSQL prevents booking overlap

**Status:** Accepted

Use `btree_gist` plus a partial GiST exclusion constraint on room equality and overlapping `tstzrange(start_at, end_at, '[)')` for confirmed bookings. Application pre-checks improve messages but cannot close concurrent races. This adds a PostgreSQL-specific migration and intentionally rules out SQLite for integration tests.

## ADR-002: The LLM extracts intent only

**Status:** Accepted

DeepSeek converts text to structured `BookingIntent`. It has no repository or booking mutation access. Pydantic and business rules validate its output, ambiguity triggers clarification, and user confirmation calls the normal `BookingService`. This contains nondeterminism and preserves a complete manual fallback.

## ADR-003: Store instants, interpret in an office timezone

**Status:** Accepted

Require offset-aware API timestamps and store them as PostgreSQL `TIMESTAMPTZ`. Interpret relative natural-language dates using configurable `OFFICE_TIMEZONE`, defaulting to `Asia/Almaty`. Use half-open intervals and convert for display at the edges.

## ADR-004: One application and explicit service boundaries

**Status:** Accepted

Use a React client, one FastAPI application, and one PostgreSQL database. Keep booking, availability, and parser responsibilities explicit. Do not add queues, caches, orchestration frameworks, or microservices without a measured need.

## ADR-005: One origin in the composed runtime

**Status:** Accepted

Nginx serves the built SPA and proxies `/api` to FastAPI. This keeps browser configuration and CORS exposure small while retaining separate frontend/backend development tooling.

## ADR-006: Liveness and readiness have different dependency scopes

**Status:** Accepted

`/health/live` reports process health without external calls. `/health/ready` runs a minimal PostgreSQL query because the database is required for application work. DeepSeek is optional and is deliberately excluded from readiness so its failure cannot disable manual booking.

## ADR-007: Request IDs and errors use one small transport contract

**Status:** Accepted

The backend accepts a bounded safe `X-Request-ID` or generates a UUID, returns it in the response, and binds it to structured logs. Expected API failures use `{"error":{"code","message","details?","request_id"}}`; logs recursively redact credential-like fields and private meeting content.

## Open decisions

The original assignment does not define these values. Do not silently choose product behavior without recording the choice and rationale:

- Default duration when natural language provides a start but no end/duration; missing critical values must never be invented.
- Booking-list ordering.
- Production deployment/TLS details; the assignment requires local Docker Compose and Nginx, not cloud deployment.

## ADR-008: Phase 02 authentication policy

**Status:** Accepted

Issue signed Bearer access tokens for 30 minutes with `sub`, `iat`, and `exp` claims; no refresh-token infrastructure is required. Registration accepts passwords from 8 through 128 characters and reports an existing normalized email as `email_already_registered` with HTTP 409. Login, including inactive accounts, always returns the same `invalid_credentials` response. Passwords use pwdlib's recommended Argon2 configuration.

## ADR-009: The public room catalog contains active rooms only

**Status:** Accepted

Authenticated users may list and retrieve active rooms. A missing or inactive room returns the same `room_not_found` response. The separate idempotent seed inserts the three assignment rooms without creating duplicates; it does not create schema at runtime.

## ADR-010: Phase 04 availability policy

**Status:** Accepted

A room schedule covers exactly one local calendar day selected by its `date` parameter in `OFFICE_TIMEZONE`, using `[day_start, next_day_start)` overlap semantics. Nearest-slot search moves forward from the requested start in 15-minute increments for at most seven days, preserves the requested duration exactly, and returns at most three choices. Conflict alternatives first return up to three active rooms free at the requested time, ordered by capacity, name, and ID; only when none qualify do they return nearest slots for the requested room.

Known participant counts set the alternative room's minimum capacity. When count is omitted, alternatives must be at least as large as the requested room. Over-capacity create requests remain validation errors. Schedule, room, alternative, and slot-search results are bounded, so Phase 04 adds no pagination. No business-hours restriction is inferred.

## ADR-011: Phase 05 AI preview and provider failures

**Status:** Accepted

Use the OpenAI Python SDK with DeepSeek's compatible base URL, a configured timeout, JSON mode, and no SDK retries. The parser receives only user text, current office-local time, timezone, and active room IDs/names/capacities. It returns an untrusted `BookingIntent`; `AIBookingService` performs catalog and domain validation and normalizes genuinely missing critical values to clarification. It never checks availability or invokes `BookingService`.

Map timeouts to `ai_timeout`/504, unavailable configuration and provider failures (including 429/5xx) to `ai_unavailable`/503, and invalid provider output to `ai_invalid_response`/502. DeepSeek configuration is supplied only to the backend container. Missing configuration disables only the AI endpoint; readiness and manual booking remain healthy. Normal tests use fakes or mocked SDK responses and make no live DeepSeek calls.

## ADR-012: Phase 06 browser session and server state

**Status:** Accepted

Keep only the short-lived access token in `sessionStorage`; passwords and user records are never persisted by the frontend. An authenticated 401 clears the token and TanStack Query cache. TanStack Query owns rooms, schedules, bookings, and mutation invalidation, while React Hook Form and Zod provide basic form feedback without reproducing backend business rules.

Manual input and editable AI previews render the same booking form and execute the same `POST /bookings` mutation. Conflict alternatives update that form and require another explicit submit. Browser AI E2E replaces only `POST /ai/booking-intent`; booking persistence and PostgreSQL remain real.
