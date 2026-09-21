## Goal

Deliver the complete functional browser experience for manual and AI-assisted meeting booking.

## Scope

`frontend/**`, required backend contract adjustments, `nginx/**`, component tests, `e2e/**`, accessibility/error-state documentation.

## Constraints

Build on phases 01–05. Use React, TypeScript, Vite, MUI, TanStack Query, React Hook Form, and Zod. Implement auth, rooms/schedules, manual booking, AI input/parsing, preview/edit/confirm, conflict alternatives, my bookings, cancellation, and loading/empty/error states. Do not duplicate backend availability, authorization, timezone, or booking rules. Keep the UI functional and accessible rather than decorative; use the one-origin `/api` route.

## Done when

All required states and flows work through the browser; AI confirmation calls the same booking API as manual entry; DeepSeek failure leaves manual booking usable; responsive/accessibility basics and component tests are present. Make one logical Conventional Commit after verification succeeds.

## Verification

Run frontend lint, typecheck, tests, and production build; backend regression checks; Compose browser smoke; Playwright manual-booking/conflict and AI-preview/confirm journeys; `git diff --check`, staged diff and secret review.
