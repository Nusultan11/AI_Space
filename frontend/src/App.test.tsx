import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("App health state", () => {
  it("shows loading while the backend request is pending", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));

    render(<App />);

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

    render(<App />);

    expect(await screen.findByText("Backend connected")).toBeInTheDocument();
  });

  it("shows a clear error when the backend request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network error")));

    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Backend unavailable: network error",
    );
  });
});
