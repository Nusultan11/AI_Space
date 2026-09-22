import { Button, Stack, Typography } from "@mui/material";

import type { BookingConflictDetails } from "../../api/types";
import { formatInstant } from "../../lib/time";

interface ConflictAlternativesProps {
  details: BookingConflictDetails;
  timezone: string;
  onRoom: (roomId: string, startAt: string, endAt: string) => void;
  onSlot: (roomId: string, startAt: string, endAt: string) => void;
}

export function ConflictAlternatives({
  details,
  timezone,
  onRoom,
  onSlot,
}: ConflictAlternativesProps) {
  return (
    <Stack spacing={1} aria-label="Booking conflict alternatives">
      <Typography component="h3" variant="subtitle1" sx={{ fontWeight: 600 }}>
        Choose an alternative, then submit again
      </Typography>
      {details.alternative_rooms.map((room) => (
        <Button
          key={room.room_id}
          variant="outlined"
          onClick={() => onRoom(room.room_id, room.start_at, room.end_at)}
        >
          Use {room.name} ({room.capacity}) at {formatInstant(room.start_at, timezone)}
        </Button>
      ))}
      {details.alternative_slots.map((slot) => (
        <Button
          key={`${slot.room_id}-${slot.start_at}`}
          variant="outlined"
          onClick={() => onSlot(slot.room_id, slot.start_at, slot.end_at)}
        >
          Use {formatInstant(slot.start_at, timezone)} – {formatInstant(slot.end_at, timezone)}
        </Button>
      ))}
    </Stack>
  );
}
