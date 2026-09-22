# E2E workspace

The Phase 01 Playwright smoke test expects the composed stack at `http://localhost:8080` and verifies the SPA plus liveness/readiness proxy paths.

```powershell
npm ci
npx playwright install chromium
npx playwright test
```

Phase 06 adds the manual and AI-assisted booking journeys.
