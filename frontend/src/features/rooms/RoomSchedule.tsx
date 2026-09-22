import { Alert, CircularProgress, List, ListItem, ListItemText, Typography } from "@mui/material";

import type { RoomSchedule as RoomScheduleType } from "../../api/types";
import { formatInstant } from "../../lib/time";

interface RoomScheduleProps {
  schedule?: RoomScheduleType;
  loading: boolean;
  error: boolean;
}

export function RoomSchedule({ schedule, loading, error }: RoomScheduleProps) {
  if (loading) {
    return <CircularProgress aria-label="Loading room schedule" size={28} />;
  }
  if (error) {
    return <Alert severity="error">Could not load this room schedule.</Alert>;
  }
  if (schedule === undefined || schedule.occupied.length === 0) {
    return <Typography>No occupied intervals for this date.</Typography>;
  }
  return (
    <List aria-label="Occupied intervals" dense>
      {schedule.occupied.map((interval) => (
        <ListItem key={`${interval.start_at}-${interval.end_at}`}>
          <ListItemText
            primary={`${formatInstant(interval.start_at, schedule.timezone)} – ${formatInstant(interval.end_at, schedule.timezone)}`}
          />
        </ListItem>
      ))}
    </List>
  );
}
