import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api } from "../../api/client";
import type { Booking } from "../../api/types";
import { browserToday, formatInstant } from "../../lib/time";

export function MyBookings() {
  const queryClient = useQueryClient();
  const bookings = useQuery({ queryKey: ["bookings"], queryFn: api.bookings });
  const rooms = useQuery({ queryKey: ["rooms"], queryFn: api.rooms });
  const timezone = useQuery({
    queryKey: ["schedule", rooms.data?.[0]?.id, browserToday()],
    queryFn: () => api.schedule(rooms.data![0].id, browserToday()),
    enabled: Boolean(rooms.data?.[0]),
  });
  const cancel = useMutation({
    mutationFn: api.cancelBooking,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["bookings"] }),
        queryClient.invalidateQueries({ queryKey: ["schedule"] }),
      ]);
    },
  });

  if (bookings.isPending || rooms.isPending) {
    return <CircularProgress aria-label="Loading my bookings" />;
  }
  if (bookings.isError || rooms.isError) {
    return <Alert severity="error">Could not load your bookings.</Alert>;
  }
  if (bookings.data.length === 0) {
    return <Typography>You have no bookings yet.</Typography>;
  }
  const roomNames = new Map(rooms.data.map((room) => [room.id, room.name]));
  const zone = timezone.data?.timezone;
  const now = Date.now();
  const ordered = [...bookings.data].sort(
    (left, right) => Date.parse(left.start_at) - Date.parse(right.start_at),
  );

  function state(booking: Booking): "Cancelled" | "Upcoming" | "In progress" | "Past" {
    if (booking.status === "cancelled") return "Cancelled";
    if (Date.parse(booking.start_at) > now) return "Upcoming";
    return Date.parse(booking.end_at) > now ? "In progress" : "Past";
  }

  return (
    <Stack spacing={2}>
      {cancel.isError && (
        <Alert severity="error">
          {cancel.error instanceof ApiError ? cancel.error.message : "Cancellation failed."}
        </Alert>
      )}
      {ordered.map((booking) => {
        const bookingState = state(booking);
        const display = (value: string) =>
          zone ? formatInstant(value, zone) : new Date(value).toLocaleString();
        return (
          <Card key={booking.id} variant="outlined">
            <CardContent>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                sx={{ justifyContent: "space-between", gap: 1 }}
              >
                <div>
                  <Typography component="h3" variant="h6">{booking.title}</Typography>
                  <Typography>{roomNames.get(booking.room_id) ?? "Room"}</Typography>
                  <Typography variant="body2">
                    {display(booking.start_at)} – {display(booking.end_at)}
                  </Typography>
                </div>
                <Stack sx={{ alignItems: { sm: "flex-end" }, gap: 1 }}>
                  <Chip label={bookingState} />
                  {bookingState === "Upcoming" && (
                    <Button
                      variant="outlined"
                      color="error"
                      disabled={cancel.isPending}
                      onClick={() => cancel.mutate(booking.id)}
                    >
                      Cancel booking
                    </Button>
                  )}
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        );
      })}
    </Stack>
  );
}
