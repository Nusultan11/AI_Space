import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/render";
import { AIBookingPanel } from "./AIBookingPanel";

const room = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "Room A",
  capacity: 6,
  description: null,
  is_active: true,
  created_at: "2030-01-01T00:00:00Z",
  updated_at: "2030-01-01T00:00:00Z",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("AIBookingPanel", () => {
  it("shows a clarification preview", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) =>
        String(input).endsWith("/rooms")
          ? jsonResponse([room])
          : jsonResponse({
              room_id: null,
              room_reference: null,
              start_at: null,
              end_at: null,
              title: null,
              participants_count: null,
              needs_clarification: true,
              missing_fields: ["start_at"],
              clarification_message: "What time should the meeting start?",
            }),
      ),
    );
    renderWithProviders(<AIBookingPanel />);
    fireEvent.change(screen.getByLabelText("Meeting request"), {
      target: { value: "Book a planning meeting" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Prepare preview" }));

    expect(await screen.findByText("What time should the meeting start?")).toBeInTheDocument();
  });

  it("shows an editable valid preview that confirms through BookingForm", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/rooms")) return jsonResponse([room]);
        if (url.includes("/schedule")) {
          return jsonResponse({
            room_id: room.id,
            date: "2030-01-02",
            timezone: "Asia/Almaty",
            day_start: "2030-01-02T00:00:00+05:00",
            day_end: "2030-01-03T00:00:00+05:00",
            occupied: [],
          });
        }
        return jsonResponse({
          room_id: room.id,
          room_reference: "Room A",
          start_at: "2030-01-02T10:00:00Z",
          end_at: "2030-01-02T11:00:00Z",
          title: "AI planning",
          participants_count: 3,
          needs_clarification: false,
          missing_fields: [],
          clarification_message: null,
        });
      }),
    );
    renderWithProviders(<AIBookingPanel />);
    fireEvent.change(screen.getByLabelText("Meeting request"), {
      target: { value: "Book Room A tomorrow" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Prepare preview" }));

    expect(await screen.findByRole("heading", { name: "Review AI preview" })).toBeVisible();
    expect(screen.getByLabelText("Meeting title")).toHaveValue("AI planning");
    expect(screen.getByLabelText("Start time")).toHaveValue("15:00");
    expect(screen.getByRole("button", { name: "Confirm booking" })).toBeInTheDocument();
  });

  it("isolates provider failure and keeps the manual path available", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) =>
        String(input).endsWith("/rooms")
          ? jsonResponse([room])
          : jsonResponse(
              { error: { code: "ai_unavailable", message: "AI booking assistance is unavailable." } },
              503,
            ),
      ),
    );
    renderWithProviders(<AIBookingPanel />);
    fireEvent.change(screen.getByLabelText("Meeting request"), {
      target: { value: "Book something" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Prepare preview" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Manual booking remains available");
    expect(screen.getByLabelText("Meeting request")).toBeEnabled();
  });
});
