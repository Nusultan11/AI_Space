import type {
  ApiErrorBody,
  AlternativeRoom,
  AlternativeSlot,
  Booking,
  BookingConflictDetails,
  BookingCreate,
  BookingIntent,
  Room,
  RoomSchedule,
  User,
} from "./types";
import { getAccessToken, notifyUnauthorized } from "../auth/session";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
    public readonly requestId?: string,
  ) {
    super(message);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isAlternativeRoom(value: unknown): value is AlternativeRoom {
  return (
    isRecord(value) &&
    typeof value.room_id === "string" &&
    typeof value.name === "string" &&
    typeof value.capacity === "number" &&
    typeof value.start_at === "string" &&
    typeof value.end_at === "string"
  );
}

function isAlternativeSlot(value: unknown): value is AlternativeSlot {
  return (
    isRecord(value) &&
    typeof value.room_id === "string" &&
    typeof value.start_at === "string" &&
    typeof value.end_at === "string"
  );
}

function normalizeError(status: number, payload: unknown): ApiError {
  if (isRecord(payload) && isRecord(payload.error)) {
    const error = payload.error as Partial<ApiErrorBody>;
    return new ApiError(
      status,
      typeof error.code === "string" ? error.code : "request_failed",
      typeof error.message === "string" ? error.message : "The request failed.",
      error.details,
      error.request_id,
    );
  }
  if (isRecord(payload) && Array.isArray(payload.detail)) {
    return new ApiError(status, "validation_error", "Please check the submitted values.");
  }
  return new ApiError(status, "request_failed", "The request could not be completed.");
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (token !== null) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "network_error", "The server is unreachable.");
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && token !== null) {
      notifyUnauthorized();
    }
    throw normalizeError(response.status, payload);
  }
  return payload as T;
}

export const api = {
  health: () => request<{ status: string }>("/health/live"),
  register: (values: { email: string; password: string; name: string }) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify(values) }),
  login: (values: { email: string; password: string }) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(values),
    }),
  currentUser: () => request<User>("/users/me"),
  rooms: () => request<Room[]>("/rooms"),
  schedule: (roomId: string, date: string) =>
    request<RoomSchedule>(`/rooms/${roomId}/schedule?date=${encodeURIComponent(date)}`),
  bookings: () => request<Booking[]>("/bookings"),
  createBooking: (values: BookingCreate) =>
    request<Booking>("/bookings", { method: "POST", body: JSON.stringify(values) }),
  cancelBooking: (bookingId: string) =>
    request<Booking>(`/bookings/${bookingId}/cancel`, { method: "POST" }),
  bookingIntent: (text: string) =>
    request<BookingIntent>("/ai/booking-intent", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
};

export function bookingConflictDetails(error: unknown): BookingConflictDetails | null {
  if (!(error instanceof ApiError) || error.code !== "booking_conflict") {
    return null;
  }
  if (!isRecord(error.details)) {
    return null;
  }
  const rooms = error.details.alternative_rooms;
  const slots = error.details.alternative_slots;
  if (!Array.isArray(rooms) || !Array.isArray(slots)) {
    return null;
  }
  if (
    !rooms.every(isAlternativeRoom) ||
    !slots.every(isAlternativeSlot)
  ) {
    return null;
  }
  return { alternative_rooms: rooms, alternative_slots: slots };
}
