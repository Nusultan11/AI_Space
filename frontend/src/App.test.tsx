import { cleanup, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
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
});
