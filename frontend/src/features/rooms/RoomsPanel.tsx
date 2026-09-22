import { Alert, Box, CircularProgress, MenuItem, Paper, TextField, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { api } from "../../api/client";
import { browserToday, todayInTimeZone } from "../../lib/time";
import { RoomSchedule } from "./RoomSchedule";

export function RoomsPanel() {
  const rooms = useQuery({ queryKey: ["rooms"], queryFn: api.rooms });
  const [roomId, setRoomId] = useState("");
  const [date, setDate] = useState(browserToday);
  const dateWasChanged = useRef(false);

  useEffect(() => {
    if (!roomId && rooms.data?.[0]) {
      setRoomId(rooms.data[0].id);
    }
  }, [roomId, rooms.data]);

  const schedule = useQuery({
    queryKey: ["schedule", roomId, date],
    queryFn: () => api.schedule(roomId, date),
    enabled: Boolean(roomId && date),
  });

  useEffect(() => {
    if (!schedule.data || dateWasChanged.current) return;
    const officeToday = todayInTimeZone(schedule.data.timezone);
    if (date !== officeToday) setDate(officeToday);
  }, [date, schedule.data]);

  return (
    <Paper component="section" aria-labelledby="rooms-heading" sx={{ p: { xs: 2, sm: 3 } }}>
      <Typography id="rooms-heading" component="h2" variant="h5" gutterBottom>
        Rooms and schedules
      </Typography>
      {rooms.isPending && <CircularProgress aria-label="Loading rooms" />}
      {rooms.isError && <Alert severity="error">Could not load rooms.</Alert>}
      {rooms.data && rooms.data.length === 0 && <Typography>No active rooms.</Typography>}
      {rooms.data && rooms.data.length > 0 && (
        <>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { sm: "2fr 1fr" }, mb: 2 }}>
            <TextField
              select
              label="Room"
              value={roomId}
              onChange={(event) => setRoomId(event.target.value)}
            >
              {rooms.data.map((room) => (
                <MenuItem key={room.id} value={room.id}>
                  {room.name} · {room.capacity} people
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Schedule date"
              type="date"
              value={date}
              onChange={(event) => {
                dateWasChanged.current = true;
                setDate(event.target.value);
              }}
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Box>
          <Typography component="h3" variant="h6" gutterBottom>
            Occupied intervals
          </Typography>
          <RoomSchedule schedule={schedule.data} loading={schedule.isPending} error={schedule.isError} />
        </>
      )}
    </Paper>
  );
}
