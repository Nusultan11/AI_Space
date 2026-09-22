export interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Room {
  id: string;
  name: string;
  capacity: number;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OccupiedInterval {
  start_at: string;
  end_at: string;
}

export interface RoomSchedule {
  room_id: string;
  date: string;
  timezone: string;
  day_start: string;
  day_end: string;
  occupied: OccupiedInterval[];
}

export interface BookingCreate {
  room_id: string;
  title: string;
  start_at: string;
  end_at: string;
  participants_count: number | null;
}

export interface Booking extends BookingCreate {
  id: string;
  user_id: string;
  status: "confirmed" | "cancelled";
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AlternativeRoom {
  room_id: string;
  name: string;
  capacity: number;
  start_at: string;
  end_at: string;
}

export interface AlternativeSlot {
  room_id: string;
  start_at: string;
  end_at: string;
}

export interface BookingConflictDetails {
  alternative_rooms: AlternativeRoom[];
  alternative_slots: AlternativeSlot[];
}

export interface BookingIntent {
  room_id: string | null;
  room_reference: string | null;
  start_at: string | null;
  end_at: string | null;
  title: string | null;
  participants_count: number | null;
  needs_clarification: boolean;
  missing_fields: string[];
  clarification_message: string | null;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
  request_id?: string;
}
