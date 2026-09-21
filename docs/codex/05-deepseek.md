## Goal

Implement safe DeepSeek-backed natural-language intent extraction that produces a preview and never creates a booking.

## Scope

`BookingIntent` schemas, parser protocol, fake and DeepSeek implementations, `/api/v1/ai/booking-intent`, configuration, tests, and AI reliability documentation.

## Constraints

Build on phases 01–04. Provide text, current local datetime, configured timezone, and room catalog to the parser. Require structured JSON, Pydantic validation, room-catalog and business validation, and clarification for ambiguous/missing critical values. Handle timeout, 429, 5xx, invalid/empty JSON, and schema errors consistently. The parser has no persistence access; confirmation remains normal `POST /bookings`; manual booking and readiness must survive DeepSeek failure. Use fake/mocks in normal CI and no real key in tests.

## Done when

Valid requests return a preview; ambiguity returns clarification; every required failure mode is mapped safely; no parser path mutates bookings; configuration is documented. Make one logical Conventional Commit after verification succeeds.

## Verification

Run parser/schema/API tests for valid, ambiguous, missing, invalid JSON/schema, timeout, 429, 5xx, and empty responses; prove no database mutation and manual fallback; run all backend checks, Compose smoke without a DeepSeek key, `git diff --check`, staged diff and secret review.
