## Goal

Harden the completed application with risk-focused tests, CI, reliable containers, observability, and concise reviewer documentation.

## Scope

Backend/frontend/E2E test gaps, `.github/workflows/**`, Dockerfiles and Compose, logging/security hardening, README and operational documentation.

## Constraints

Build on phases 01–06. Prioritize authentication/authorization, PostgreSQL constraints and concurrency, timezone boundaries, AI failure isolation, migrations/seed, and the two E2E journeys—not a coverage target. CI must use real PostgreSQL and mocked DeepSeek, run backend and frontend gates, practical E2E, and Docker builds. Logs need request IDs and redaction. Keep secrets out of repository/CI defaults and avoid new product features.

## Done when

The clean Compose path is repeatable; CI covers every required gate; critical tests are stable; logs are structured and safe; README fully explains operation, decisions, trade-offs, limitations, and checks. Make one logical Conventional Commit after verification succeeds.

## Verification

Run the exact clean-machine Compose procedure; backend format/lint/type/all tests; frontend lint/type/all tests/build; Playwright; Docker image builds; migration and seed replay; `git diff --check`, staged diff, dependency and secret review.
