## Goal

Implement correct manual booking and cancellation with database-enforced non-overlap under concurrency.

## Scope

Booking model/status/migration, PostgreSQL extension and exclusion constraint, `BookingService`, booking repositories/routes, error translation, tests, and affected documentation.

## Constraints

Build on phases 01–02. Use aware `TIMESTAMPTZ` values and `[start, end)` semantics. Both future manual and AI confirmation must call this service. Validate room, interval, past time, ownership, status, and documented capacity policy. Friendly conflict checks are advisory; catch the named PostgreSQL constraint violation, roll back, and return HTTP 409. Preserve cancelled rows. No availability search beyond the minimum needed for conflict correctness.

## Done when

Users create/list/read/cancel their own bookings; cannot cancel another user's booking; constraints and migrations are correct; boundary and rollback tests pass; two concurrent identical requests yield one success, one conflict, and one confirmed row. Make one logical Conventional Commit after verification succeeds.

## Verification

Run focused service/API tests plus real-PostgreSQL migration, interval, cancellation, authorization, and concurrency tests; then all backend checks, Compose smoke, `git diff --check`, staged diff and secret review.
