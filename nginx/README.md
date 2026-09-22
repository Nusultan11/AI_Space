# Nginx workspace

The multi-stage Dockerfile builds the React application and serves it with Nginx. `default.conf` proxies `/api/*` to FastAPI, forwards standard proxy headers, and falls back to `index.html` for client-side routes. Compose exposes this service at `http://localhost:8080`.
