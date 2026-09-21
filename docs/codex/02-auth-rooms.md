## Goal

Implement secure user authentication and the read-only room catalog on the verified foundation from phase 01.

## Scope

Backend user/room models, migrations, repositories/services, auth dependencies and `/api/v1` routes, idempotent room seed, tests, and affected API documentation.

## Constraints

Read the project instructions and previous phase diff first. Use UUIDs, normalized unique emails, Argon2 via pwdlib, PyJWT Bearer auth, timezone-aware audit fields, and one error schema. Seed the three required Russian-named rooms idempotently. Authenticated users may read rooms; do not add admin/RBAC or booking behavior. Record decisions instead of guessing unspecified policy. Never log credentials or tokens.

## Done when

Register, login, current user, room list/detail, migrations, and repeatable seed work against PostgreSQL; authorization and failure cases have unit/integration coverage; documentation is current. Make one logical Conventional Commit after verification succeeds.

## Verification

Run focused auth/room tests, migration upgrade from empty PostgreSQL, seed twice, full backend format/lint/type/test checks, Compose smoke, `git diff --check`, staged diff and secret review.
