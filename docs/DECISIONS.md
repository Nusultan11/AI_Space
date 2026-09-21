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

## Open decisions

The original assignment does not define these values. Do not silently choose product behavior without recording the choice and rationale:

- JWT lifetime and whether refresh tokens are required (only Bearer JWT is required).
- Registration password policy and duplicate-email disclosure behavior.
- Whether inactive rooms remain visible in historical schedules.
- Participant-capacity behavior when participant count is omitted, and whether over-capacity is an error or alternative-search trigger.
- Default duration when natural language provides a start but no end/duration; missing critical values must never be invented.
- Search horizon and granularity for “nearest free slot.”
- Default schedule window, pagination shape, and booking-list ordering.
- Production deployment/TLS details; the assignment requires local Docker Compose and Nginx, not cloud deployment.
