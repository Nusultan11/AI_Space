import { Alert, Button, CircularProgress, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, api } from "../../api/client";
import type { BookingIntent } from "../../api/types";
import { instantToLocalInput } from "../../lib/time";
import { BookingForm, type BookingFormValues } from "../bookings/BookingForm";

function previewValues(intent: BookingIntent, timezone: string): Partial<BookingFormValues> {
  const start = intent.start_at ? instantToLocalInput(intent.start_at, timezone) : undefined;
  const end = intent.end_at ? instantToLocalInput(intent.end_at, timezone) : undefined;
  return {
    room_id: intent.room_id ?? undefined,
    date: start?.date,
    start_time: start?.time,
    end_time: end?.time,
    title: intent.title ?? undefined,
    participants_count: intent.participants_count?.toString() ?? "",
  };
}

export function AIBookingPanel() {
  const [text, setText] = useState("");
  const [intent, setIntent] = useState<BookingIntent | null>(null);
  const rooms = useQuery({ queryKey: ["rooms"], queryFn: api.rooms });
  const parse = useMutation({
    mutationFn: api.bookingIntent,
    onSuccess: setIntent,
  });
  const previewSchedule = useQuery({
    queryKey: ["schedule", intent?.room_id, intent?.start_at?.slice(0, 10)],
    queryFn: () => api.schedule(intent!.room_id!, intent!.start_at!.slice(0, 10)),
    enabled: Boolean(
      intent && !intent.needs_clarification && intent.room_id && intent.start_at,
    ),
  });

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setIntent(null);
    parse.mutate(text);
  }

  return (
    <Stack spacing={3}>
      <Paper component="form" onSubmit={submit} sx={{ p: { xs: 2, sm: 3 } }}>
        <Typography component="h2" variant="h5" gutterBottom>AI booking preview</Typography>
        <Typography sx={{ mb: 2 }}>
          Describe the meeting. Review and edit every value before confirmation.
        </Typography>
        {parse.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {parse.error instanceof ApiError
              ? parse.error.message
              : "AI booking assistance is unavailable."} Manual booking remains available.
          </Alert>
        )}
        <TextField
          label="Meeting request"
          value={text}
          onChange={(event) => setText(event.target.value)}
          multiline
          minRows={3}
          fullWidth
          slotProps={{ htmlInput: { maxLength: 2000 } }}
        />
        <Button
          type="submit"
          variant="contained"
          sx={{ mt: 2 }}
          disabled={parse.isPending || !text.trim()}
        >
          {parse.isPending ? "Preparing preview…" : "Prepare preview"}
        </Button>
        {parse.isPending && <CircularProgress aria-label="Parsing booking request" size={24} sx={{ ml: 2 }} />}
      </Paper>
      {intent?.needs_clarification && (
        <Alert severity="info">
          {intent.clarification_message ?? "Please clarify the booking details."}
        </Alert>
      )}
      {intent && !intent.needs_clarification && rooms.isError && (
        <Alert severity="error">Could not load rooms for the AI preview.</Alert>
      )}
      {intent && !intent.needs_clarification && previewSchedule.isError && (
        <Alert severity="error">Could not load the AI preview schedule. Try again later.</Alert>
      )}
      {intent && !intent.needs_clarification && rooms.data && previewSchedule.data && (
        <Paper sx={{ p: { xs: 2, sm: 3 } }}>
          <Typography component="h2" variant="h5" gutterBottom>Review AI preview</Typography>
          <BookingForm
            key={`${intent.room_id}-${intent.start_at}-${intent.end_at}`}
            rooms={rooms.data}
            initialValues={previewValues(intent, previewSchedule.data.timezone)}
            submitLabel="Confirm booking"
          />
        </Paper>
      )}
    </Stack>
  );
}
