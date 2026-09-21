## Goal

Create a runnable monorepo foundation that starts from a clean machine and fixes the shared API, configuration, logging, migration, and developer-tooling contracts.

## Scope

`backend/**`, `frontend/**`, `e2e/**`, `nginx/**`, `compose.yaml`, `.env.example`, `.github/workflows/**`, root documentation.

## Constraints

Read `AGENTS.md`, `docs/TASK.md`, `docs/ARCHITECTURE.md`, and `docs/DECISIONS.md` first. Bootstrap the specified stack without product features or speculative infrastructure. PostgreSQL must have a healthcheck; add initial Alembic plumbing, FastAPI liveness/readiness, React shell, Nginx `/api` proxy, request IDs, structured redacted logging, locked project-local dependencies, and safe configuration. Resolve only foundation-level open decisions and record them. Do not commit secrets.

## Done when

`docker compose up --build` exposes one working URL, migrations can run on an empty database, liveness/readiness semantics are tested, frontend reaches the backend, tool configs are operational, and concise setup documentation is current. Make one logical Conventional Commit after verification succeeds.

## Verification

Run Compose config/start/health checks; backend Ruff, Pyright, and pytest; frontend lint, typecheck, tests, and build; Playwright smoke where practical; `git diff --check`; staged diff and secret review.
