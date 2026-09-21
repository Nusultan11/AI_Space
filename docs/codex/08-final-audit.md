## Goal

Audit the finished repository against every original requirement and fix only confirmed defects.

## Scope

Original task, `AGENTS.md`, all docs, implementation, migrations, tests, Compose/Nginx, CI, README, and Git diff/history.

## Constraints

Build on phases 01–07. Trace each requirement to code and verification evidence. Re-test clean startup, migrations/seed, auth/authorization, interval boundaries, database exclusion and concurrency, timezone behavior, availability alternatives, AI ambiguity/failures, manual fallback, browser flows, logs, and secrets. Reproduce defects, make the smallest correct fix, add regression coverage, and avoid speculative features or unrelated refactors.

## Done when

Every mandatory requirement has PASS/FAIL evidence; all confirmed defects are resolved; clean Docker startup and the full gate pass; docs match reality; known limitations are explicit and no secrets are present. Make one logical Conventional Commit after verification succeeds, or document a genuine external blocker without claiming completion.

## Verification

Run clean `docker compose up --build`; all backend, frontend, PostgreSQL integration, and Playwright checks; Docker builds; migration/seed replay; `git diff --check`; full diff, staged diff, secret scan, and concise Git-history review.
