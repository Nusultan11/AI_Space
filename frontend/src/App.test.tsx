import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { setAccessToken } from "./auth/session";
import { renderWithProviders } from "./test/render";

afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

describe("App health state", () => {
  it("shows loading while the backend request is pending", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));

    renderWithProviders(<App />);

    expect(screen.getByRole("status")).toHaveTextContent("Checking backend health");
  });

  it("shows success after a healthy backend response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok" }),
      }),
    );

    renderWithProviders(<App />);

    expect(await screen.findByText("Backend connected")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Sign in" })).toBeVisible();
  });

  it("shows a clear error when the backend request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network error")));

    renderWithProviders(<App />);

    expect(await screen.findByText("Backend unavailable")).toBeInTheDocument();
  });

  it("shows a room-loading failure on manual booking", async () => {
    setAccessToken("test-token");
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/health/live")) return new Response(JSON.stringify({ status: "ok" }));
      if (url.endsWith("/users/me")) return new Response(JSON.stringify({ id: "user-1", name: "Test" }));
      if (url.endsWith("/rooms")) return new Response(JSON.stringify({ error: { code: "unavailable", message: "Unavailable" } }), { status: 503 });
      throw new Error(`Unexpected request ${url}`);
    }));
    renderWithProviders(<App />);
    fireEvent.click(await screen.findByRole("tab", { name: "Manual booking" }));
    expect(await screen.findByText("Could not load rooms. Try again later.")).toBeVisible();
  });

  it("labels cancelled, upcoming, in-progress, and past bookings separately", async () => {
    setAccessToken("test-token");
    const now = Date.now();
    const at = (offsetMinutes: number) => new Date(now + offsetMinutes * 60_000).toISOString();
    const bookings = [
      { id: "cancelled", title: "Cancelled meeting", status: "cancelled", start_at: at(60), end_at: at(120) },
      { id: "upcoming", title: "Upcoming meeting", status: "confirmed", start_at: at(60), end_at: at(120) },
      { id: "ongoing", title: "Ongoing meeting", status: "confirmed", start_at: at(-30), end_at: at(30) },
      { id: "past", title: "Past meeting", status: "confirmed", start_at: at(-120), end_at: at(-60) },
    ].map((booking) => ({ ...booking, room_id: "room-1" }));
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/health/live")) return new Response(JSON.stringify({ status: "ok" }));
      if (url.endsWith("/users/me")) return new Response(JSON.stringify({ id: "user-1", name: "Test" }));
      if (url.endsWith("/rooms")) return new Response(JSON.stringify([]));
      if (url.endsWith("/bookings")) return new Response(JSON.stringify(bookings));
      throw new Error(`Unexpected request ${url}`);
    }));
    renderWithProviders(<App />);
    fireEvent.click(await screen.findByRole("tab", { name: "My bookings" }));
    for (const label of ["Cancelled", "Upcoming", "In progress", "Past"]) {
      expect(await screen.findByText(label)).toBeVisible();
    }
  });
});
