import { zodResolver } from "@hookform/resolvers/zod";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { ApiError, api, bookingConflictDetails } from "../../api/client";
import type { Booking, BookingConflictDetails, Room } from "../../api/types";
import {
  browserToday,
  instantToLocalInput,
  localDateTimeToIso,
  todayInTimeZone,
} from "../../lib/time";
import { ConflictAlternatives } from "./ConflictAlternatives";

const bookingSchema = z
  .object({
    room_id: z.string().min(1, "Choose a room."),
    date: z.string().min(1, "Choose a date."),
    start_time: z.string().min(1, "Choose a start time."),
    end_time: z.string().min(1, "Choose an end time."),
    title: z.string().trim().min(1, "Enter a title."),
    participants_count: z.string().refine(
      (value) =>
        value === "" || (Number.isInteger(Number(value)) && Number(value) >= 1),
      "Enter a whole number of at least 1.",
    ),
  })
  .refine((values) => values.end_time > values.start_time, {
    path: ["end_time"],
    message: "End time must be after start time.",
  });

export type BookingFormValues = z.infer<typeof bookingSchema>;

interface BookingFormProps {
  rooms: Room[];
  initialValues?: Partial<BookingFormValues>;
  submitLabel?: string;
  onSuccess?: (booking: Booking) => void;
}

export function BookingForm({
  rooms,
  initialValues,
  submitLabel = "Create booking",
  onSuccess,
}: BookingFormProps) {
  const queryClient = useQueryClient();
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<BookingConflictDetails | null>(null);
  const preserveDate = useRef(initialValues?.date !== undefined);
  const form = useForm<BookingFormValues>({
    resolver: zodResolver(bookingSchema),
    defaultValues: {
      room_id: initialValues?.room_id ?? rooms[0]?.id ?? "",
      date: initialValues?.date ?? browserToday(),
      start_time: initialValues?.start_time ?? "09:00",
      end_time: initialValues?.end_time ?? "10:00",
      title: initialValues?.title ?? "",
      participants_count: initialValues?.participants_count ?? "",
    },
  });
  const roomId = form.watch("room_id");
  const date = form.watch("date");
  const schedule = useQuery({
    queryKey: ["schedule", roomId, date],
    queryFn: () => api.schedule(roomId, date),
    enabled: Boolean(roomId && date),
  });

  useEffect(() => {
    if (!schedule.data || preserveDate.current) return;
    const officeToday = todayInTimeZone(schedule.data.timezone);
    if (date !== officeToday) {
      form.setValue("date", officeToday, { shouldValidate: true });
    }
  }, [date, form, schedule.data]);

  const createBooking = useMutation({
    mutationFn: api.createBooking,
    onSuccess: async (booking) => {
      setConflict(null);
      setError(null);
      setSuccess("Booking confirmed.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["bookings"] }),
        queryClient.invalidateQueries({ queryKey: ["schedule"] }),
      ]);
      onSuccess?.(booking);
    },
    onError: (caught) => {
      setSuccess(null);
      const details = bookingConflictDetails(caught);
      setConflict(details);
      setError(caught instanceof ApiError ? caught.message : "Booking could not be created.");
    },
  });

  const submit = form.handleSubmit((values) => {
    setSuccess(null);
    setError(null);
    setConflict(null);
    if (!schedule.data) {
      setError("Wait for the room timezone to load, then try again.");
      return;
    }
    try {
      createBooking.mutate({
        room_id: values.room_id,
        title: values.title.trim(),
        start_at: localDateTimeToIso(values.date, values.start_time, schedule.data.timezone),
        end_at: localDateTimeToIso(values.date, values.end_time, schedule.data.timezone),
        participants_count: values.participants_count
          ? Number(values.participants_count)
          : null,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Invalid local time.");
    }
  });

  function applyAlternative(room: string, startAt: string, endAt: string) {
    if (!schedule.data) return;
    const start = instantToLocalInput(startAt, schedule.data.timezone);
    const end = instantToLocalInput(endAt, schedule.data.timezone);
    form.setValue("room_id", room, { shouldValidate: true });
    form.setValue("date", start.date, { shouldValidate: true });
    form.setValue("start_time", start.time, { shouldValidate: true });
    form.setValue("end_time", end.time, { shouldValidate: true });
    setConflict(null);
    setError(null);
  }

  return (
    <Box component="form" onSubmit={submit} noValidate>
      <Stack spacing={2}>
        {success && <Alert severity="success">{success}</Alert>}
        {error && <Alert severity="error">{error}</Alert>}
        <Controller
          name="room_id"
          control={form.control}
          render={({ field, fieldState }) => (
            <TextField
              {...field}
              select
              label="Room"
              error={Boolean(fieldState.error)}
              helperText={fieldState.error?.message}
            >
              {rooms.map((room) => (
                <MenuItem key={room.id} value={room.id}>
                  {room.name} · {room.capacity} people
                </MenuItem>
              ))}
            </TextField>
          )}
        />
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { sm: "1fr 1fr 1fr" } }}>
          <TextField
            label="Date"
            type="date"
            {...form.register("date", {
              onChange: () => {
                preserveDate.current = true;
              },
            })}
            error={Boolean(form.formState.errors.date)}
            helperText={form.formState.errors.date?.message}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <TextField
            label="Start time"
            type="time"
            {...form.register("start_time")}
            error={Boolean(form.formState.errors.start_time)}
            helperText={form.formState.errors.start_time?.message}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <TextField
            label="End time"
            type="time"
            {...form.register("end_time")}
            error={Boolean(form.formState.errors.end_time)}
            helperText={form.formState.errors.end_time?.message}
            slotProps={{ inputLabel: { shrink: true } }}
          />
        </Box>
        <TextField
          label="Meeting title"
          {...form.register("title")}
          error={Boolean(form.formState.errors.title)}
          helperText={form.formState.errors.title?.message}
        />
        <TextField
          label="Participants (optional)"
          type="number"
          slotProps={{ htmlInput: { min: 1 } }}
          {...form.register("participants_count")}
          error={Boolean(form.formState.errors.participants_count)}
          helperText={form.formState.errors.participants_count?.message}
        />
        {schedule.isPending && (
          <Typography role="status"><CircularProgress size={18} /> Loading room timezone…</Typography>
        )}
        {schedule.isError && <Alert severity="error">Could not load room context.</Alert>}
        {conflict && schedule.data && (
          <ConflictAlternatives
            details={conflict}
            timezone={schedule.data.timezone}
            onRoom={applyAlternative}
            onSlot={applyAlternative}
          />
        )}
        <Button type="submit" variant="contained" disabled={createBooking.isPending || !schedule.data}>
          {createBooking.isPending ? "Saving…" : submitLabel}
        </Button>
      </Stack>
    </Box>
  );
}
