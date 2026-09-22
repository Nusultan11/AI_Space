import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/render";
import { AuthScreen } from "./AuthScreen";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

describe("AuthScreen", () => {
  it("registers, signs in, and stores only the access token", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ id: "user-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ access_token: "test-token", token_type: "bearer" }));
    vi.stubGlobal("fetch", fetchMock);
    const authenticated = vi.fn();
    renderWithProviders(<AuthScreen onAuthenticated={authenticated} />);

    fireEvent.click(screen.getByRole("tab", { name: "Register" }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Ada" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ada@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => expect(authenticated).toHaveBeenCalledWith("test-token"));
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(String(fetchMock.mock.calls[0][0])).toContain("/auth/register");
    expect(String(fetchMock.mock.calls[1][0])).toContain("/auth/login");
    expect(sessionStorage.length).toBe(1);
    expect(sessionStorage.getItem("aispace.access-token")).toBe("test-token");
  });

  it("shows the normalized authentication error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          { error: { code: "invalid_credentials", message: "Invalid email or password." } },
          401,
        ),
      ),
    );
    renderWithProviders(<AuthScreen onAuthenticated={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ada@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
  });
});
