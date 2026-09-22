import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Room } from "../../api/types";
import { todayInTimeZone } from "../../lib/time";
import { renderWithProviders } from "../../test/render";
import { BookingForm } from "./BookingForm";

const room: Room = {
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

function schedule(date: string) {
  return {
    room_id: room.id,
    date,
    timezone: "Asia/Almaty",
    day_start: `${date}T00:00:00+05:00`,
    day_end: `${date}T00:00:00+05:00`,
    occupied: [],
  };
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("BookingForm", () => {
  it("normalizes the untouched default date to office-local today", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    const now = new Date("2030-01-01T12:00:00Z");
    vi.setSystemTime(now);
    expect(todayInTimeZone("UTC", now)).toBe("2030-01-01");
    expect(todayInTimeZone("Pacific/Kiritimati", now)).toBe("2030-01-02");

    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      const date = url.searchParams.get("date");
      if (url.pathname.includes("/schedule") && date) {
        return jsonResponse({ ...schedule(date), timezone: "Pacific/Kiritimati" });
      }
      throw new Error(`Unexpected request ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderWithProviders(<BookingForm rooms={[room]} />);

    const dateInput = screen.getByLabelText("Date");
    await waitFor(() => expect(dateInput).toHaveValue("2030-01-02"));

    fireEvent.change(dateInput, { target: { value: "2030-01-05" } });
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([input]) => String(input).includes("date=2030-01-05"))).toBe(
        true,
      ),
    );
    expect(dateInput).toHaveValue("2030-01-05");
  });

  it("submits an offset-aware booking through the normal booking endpoint", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/schedule")) return jsonResponse(schedule("2030-01-02"));
      if (url.endsWith("/bookings") && init?.method === "POST") {
        return jsonResponse({ id: "booking-1", status: "confirmed" }, 201);
      }
      throw new Error(`Unexpected request ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderWithProviders(
      <BookingForm
        rooms={[room]}
        initialValues={{ date: "2030-01-02", start_time: "10:00", end_time: "11:00" }}
      />,
    );

    fireEvent.change(screen.getByLabelText("Meeting title"), { target: { value: "Planning" } });
    const submit = screen.getByRole("button", { name: "Create booking" });
    await waitFor(() => expect(submit).toBeEnabled());
    fireEvent.click(submit);

    expect(await screen.findByText("Booking confirmed.")).toBeInTheDocument();
    const bookingCall = fetchMock.mock.calls.find(
      ([input, init]) => String(input).endsWith("/bookings") && init?.method === "POST",
    );
    expect(bookingCall).toBeDefined();
    const payload = JSON.parse(String(bookingCall?.[1]?.body));
    expect(payload.start_at).toBe("2030-01-02T05:00:00.000Z");
    expect(payload.room_id).toBe(room.id);
  });

  it("renders typed conflict alternatives and applies one without resubmitting", async () => {
    const alternativeId = "22222222-2222-4222-8222-222222222222";
    const rooms = [{ ...room }, { ...room, id: alternativeId, name: "Room B" }];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/schedule")) return jsonResponse(schedule("2030-01-02"));
      if (url.endsWith("/bookings") && init?.method === "POST") {
        return jsonResponse(
          {
            error: {
              code: "booking_conflict",
              message: "The room is already booked for this time.",
              details: {
                alternative_rooms: [
                  {
                    room_id: alternativeId,
                    name: "Room B",
                    capacity: 6,
                    start_at: "2030-01-02T10:00:00+05:00",
                    end_at: "2030-01-02T11:00:00+05:00",
                  },
                ],
                alternative_slots: [],
              },
            },
          },
          409,
        );
      }
      throw new Error(`Unexpected request ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderWithProviders(
      <BookingForm
        rooms={rooms}
        initialValues={{ date: "2030-01-02", start_time: "10:00", end_time: "11:00" }}
      />,
    );

    fireEvent.change(screen.getByLabelText("Meeting title"), { target: { value: "Overlap" } });
    const submit = screen.getByRole("button", { name: "Create booking" });
    await waitFor(() => expect(submit).toBeEnabled());
    fireEvent.click(submit);

    const alternative = await screen.findByRole("button", { name: /Use Room B/ });
    const postCount = fetchMock.mock.calls.filter(([, init]) => init?.method === "POST").length;
    fireEvent.click(alternative);
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(postCount);
    expect(screen.queryByLabelText("Booking conflict alternatives")).not.toBeInTheDocument();
  });
});
