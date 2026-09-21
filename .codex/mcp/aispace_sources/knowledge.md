# AiSpace engineering guidance

This cheat sheet summarizes project-specific reasoning. Repository requirements, architecture decisions, and migrations remain the final contract.

## Architecture boundaries

- **What matters:** Keep routers thin, domain decisions in services, persistence in SQLAlchemy/PostgreSQL, and browser concerns in React. PostgreSQL is the source of truth.
- **Common mistake:** Letting routers, UI components, or the LLM duplicate booking rules and create competing sources of truth.
- **Sources:** `fastapi`, `sqlalchemy_asyncio`, `pydantic`

## Booking invariant

- **What matters:** A confirmed booking may not overlap another confirmed booking for the same room. Enforce this independently of every calling path.
- **Common mistake:** Treating an availability query as a guarantee and assuming sequential requests.
- **Sources:** `pg_constraints`, `pg_range_types`, `pg_transaction_isolation`

## PostgreSQL overlap protection

- **What matters:** Enable `btree_gist` and use a partial GiST exclusion constraint combining `room_id WITH =` and `tstzrange(start_at, end_at, '[)') WITH &&` for confirmed rows.
- **Common mistake:** Replacing the database constraint with only `SELECT`-then-`INSERT`, or forgetting that cancelled rows must not block the slot.
- **Sources:** `pg_range_types`, `pg_constraints`, `pg_btree_gist`

## Half-open interval semantics

- **What matters:** Booking intervals are `[start, end)`, so 14:00–15:00 and 15:00–16:00 are adjacent, not overlapping.
- **Common mistake:** Mixing inclusive-end comparisons across SQL, Python, and frontend displays.
- **Sources:** `pg_range_types`

## Timezone-aware timestamps

- **What matters:** Require offset-aware API inputs, store instants as `TIMESTAMPTZ`, and interpret relative language in configured `OFFICE_TIMEZONE` (default `Asia/Almaty`).
- **Common mistake:** Persisting naive local timestamps or asking the LLM to settle timezone conversions.
- **Sources:** `pg_datetime`, `pydantic`

## Application pre-check and database guarantee

- **What matters:** Pre-check availability for a friendly response, then rely on the exclusion constraint as the final atomic decision and translate its named violation after rollback.
- **Common mistake:** Returning success because the pre-check passed, or reusing a failed transaction before rollback.
- **Sources:** `pg_constraints`, `pg_transaction_isolation`, `sqlalchemy_asyncio`

## Concurrency and race conditions

- **What matters:** Test two concurrent inserts for the same room/time; one must succeed, one must conflict, and exactly one confirmed row must remain.
- **Common mistake:** Writing only single-threaded overlap tests or weakening isolation instead of enforcing the invariant.
- **Sources:** `pg_transaction_isolation`, `testcontainers_python`, `pytest`

## Shared BookingService path

- **What matters:** Manual creation and confirmation of an AI preview both call the same `BookingService` for room, interval, past-time, capacity, conflict, transaction, and authorization rules.
- **Common mistake:** Giving the AI endpoint a shortcut that creates rows or validates differently from the manual endpoint.
- **Sources:** `fastapi`, `pydantic`, `sqlalchemy_asyncio`

## DeepSeek is a parser only

- **What matters:** DeepSeek maps text plus current local time, timezone, and room catalog to a previewable `BookingIntent`; confirmation uses normal `POST /bookings`.
- **Common mistake:** Allowing the model or parser integration to access persistence or claim a booking succeeded.
- **Sources:** `deepseek_api`, `deepseek_json_output`, `openai_python`

## Untrusted LLM output

- **What matters:** Parse structured JSON, validate it with Pydantic, then apply catalog and business validation before showing a preview.
- **Common mistake:** Assuming valid JSON is valid intent, or accepting a room ID not present in the supplied catalog.
- **Sources:** `deepseek_json_output`, `pydantic`

## Ambiguity and clarification

- **What matters:** Missing or ambiguous critical room/date/time values produce `needs_clarification`, explicit missing fields, and a useful clarification message.
- **Common mistake:** Inventing a date, duration, room, or participant count to force a complete intent.
- **Sources:** `deepseek_json_output`, `pydantic`

## AI failure isolation

- **What matters:** Bound external calls and handle timeout, 429, 5xx, empty output, invalid JSON, and schema failures. Manual booking and backend readiness remain available.
- **Common mistake:** Making optional DeepSeek connectivity a readiness dependency or returning provider internals to users.
- **Sources:** `deepseek_api`, `openai_python`, `google_sre_book`

## JWT, passwords, and authorization

- **What matters:** Hash passwords with Argon2, validate signed short-lived access tokens and claims, and authorize booking ownership on every protected operation.
- **Common mistake:** Logging credentials/tokens, storing plaintext passwords, or treating authentication as authorization to cancel any booking.
- **Sources:** `jwt_rfc7519`, `owasp_authentication`, `owasp_password_storage`, `owasp_rest_security`

## Conflict alternatives as business value

- **What matters:** Help the user arrange the meeting: first suggest a suitable free room at the requested time, then the nearest slot for the requested room.
- **Common mistake:** Returning an opaque 409 without actionable options or ignoring known room capacity.
- **Sources:** `pg_range_types`, `tanstack_query`, `mui`

## Migrations

- **What matters:** Alembic owns tables, indexes, `btree_gist`, checks, foreign keys, and the named exclusion constraint; seed rooms separately and idempotently.
- **Common mistake:** Creating schema ad hoc at application startup or trusting autogenerated PostgreSQL-specific operations without review.
- **Sources:** `alembic`, `pg_btree_gist`, `pg_constraints`

## Docker startup

- **What matters:** `docker compose up --build` starts PostgreSQL health, migrations, idempotent seed, backend, and Nginx frontend in dependency order with one browser origin.
- **Common mistake:** Using startup order without health conditions, embedding secrets, or letting the app race pending migrations.
- **Sources:** `docker_compose`, `nginx_reverse_proxy`, `twelve_factor_config`

## Testing pyramid

- **What matters:** Use unit tests for rules, API tests for contracts, real PostgreSQL for migrations/constraints/concurrency, mocked DeepSeek for failures, and Playwright for the two critical browser journeys.
- **Common mistake:** Using SQLite for PostgreSQL behavior, testing only happy paths, or pushing all correctness checks into slow E2E tests.
- **Sources:** `pytest`, `testcontainers_python`, `playwright`

## Frontend server state and booking flow

- **What matters:** TanStack Query owns server state and invalidation; React Hook Form and Zod provide form feedback; AI results are editable previews before confirmation.
- **Common mistake:** Reimplementing availability rules in the browser or leaving stale schedules after create/cancel mutations.
- **Sources:** `react`, `typescript`, `tanstack_query`, `react_hook_form`, `zod`, `mui`

## Observability

- **What matters:** Propagate request IDs, emit structured actionable logs, distinguish liveness/readiness, and redact credentials, tokens, authorization headers, keys, and unnecessary meeting text.
- **Common mistake:** Logging sensitive payloads or reporting optional DeepSeek failure as total service unavailability.
- **Sources:** `google_sre_book`, `owasp_rest_security`, `docker_compose`

## Interview trade-offs

- **What matters:** Explain why one application, PostgreSQL constraints, deterministic services, preview-before-confirmation, and mocked external AI maximize correctness and reviewability for this scope.
- **Common mistake:** Adding queues, caches, microservices, agent frameworks, or vector search without a measured requirement.
- **Sources:** `pg_constraints`, `fastapi`, `deepseek_json_output`, `google_sre_book`
