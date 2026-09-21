## Goal

Add deterministic schedules, free-room search, and useful conflict alternatives without weakening booking integrity.

## Scope

`AvailabilityService`, room schedule and `/api/v1/availability` routes, conflict response enrichment, query tests, performance checks, and API documentation.

## Constraints

Build on phases 01–03 and reuse their interval rules. PostgreSQL remains authoritative. Prefer a suitable room with enough known capacity at the requested time, then the nearest slot for the requested room. Define and document search granularity/horizon and pagination/window defaults before implementing them. Keep calculations out of the LLM and frontend; avoid caches and premature abstraction.

## Done when

Schedules, free-room queries, nearest slots, and deterministic alternatives work for adjacent, overlapping, cancelled, capacity, empty, and timezone-edge cases; conflict responses use the shared schema; query behavior is acceptably bounded. Make one logical Conventional Commit after verification succeeds.

## Verification

Run focused availability unit/API tests and real-PostgreSQL edge/integration tests; inspect representative query plans if needed; run all backend checks, Compose smoke, `git diff --check`, staged diff and secret review.
