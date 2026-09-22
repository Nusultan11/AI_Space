# Frontend workspace

The Phase 01 React/Vite shell calls `/api/v1/health/live` and renders loading, connected, or error state. Product UI remains deferred to Phase 06.

```powershell
npm ci
npm run dev
```

The development server proxies `/api` to `http://localhost:8000`. Run the gate with `npm run lint`, `npm run typecheck`, `npm test -- --run`, and `npm run build`.
