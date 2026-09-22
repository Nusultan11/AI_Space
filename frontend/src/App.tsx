import { useEffect, useState } from "react";

type HealthState =
  | { kind: "loading" }
  | { kind: "success" }
  | { kind: "error"; message: string };

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export default function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    async function loadHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/health/live`, {
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`Health request failed with status ${response.status}`);
        }
        const payload: unknown = await response.json();
        if (
          typeof payload !== "object" ||
          payload === null ||
          !("status" in payload) ||
          payload.status !== "ok"
        ) {
          throw new Error("Health response had an unexpected shape");
        }
        setHealth({ kind: "success" });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        setHealth({
          kind: "error",
          message: error instanceof Error ? error.message : "Backend is unavailable",
        });
      }
    }

    void loadHealth();
    return () => controller.abort();
  }, []);

  return (
    <main
      style={{
        maxWidth: "42rem",
        margin: "5rem auto",
        padding: "0 1.5rem",
        fontFamily: "system-ui, sans-serif",
        lineHeight: 1.5,
      }}
    >
      <h1>AiSpace</h1>
      <p>Meeting-room booking foundation</p>
      {health.kind === "loading" && <p role="status">Checking backend health…</p>}
      {health.kind === "success" && <p role="status">Backend connected</p>}
      {health.kind === "error" && (
        <p role="alert">Backend unavailable: {health.message}</p>
      )}
    </main>
  );
}
