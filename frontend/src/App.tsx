import {
  Alert,
  AppBar,
  Box,
  Button,
  Container,
  Paper,
  Tab,
  Tabs,
  Toolbar,
  Typography,
} from "@mui/material";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "./api/client";
import { clearAccessToken, getAccessToken, UNAUTHORIZED_EVENT } from "./auth/session";
import { AIBookingPanel } from "./features/ai-booking/AIBookingPanel";
import { AuthScreen } from "./features/auth/AuthScreen";
import { BookingForm } from "./features/bookings/BookingForm";
import { MyBookings } from "./features/bookings/MyBookings";
import { RoomsPanel } from "./features/rooms/RoomsPanel";

export default function App() {
  const queryClient = useQueryClient();
  const [token, setToken] = useState(getAccessToken);
  const [tab, setTab] = useState(0);
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
  const currentUser = useQuery({
    queryKey: ["current-user", token],
    queryFn: api.currentUser,
    enabled: token !== null,
  });
  const rooms = useQuery({ queryKey: ["rooms"], queryFn: api.rooms, enabled: token !== null });

  useEffect(() => {
    function unauthorized() {
      queryClient.clear();
      setToken(null);
    }
    window.addEventListener(UNAUTHORIZED_EVENT, unauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, unauthorized);
  }, [queryClient]);

  function logout() {
    clearAccessToken();
    queryClient.clear();
    setToken(null);
    setTab(0);
  }

  const healthStatus = health.isPending
    ? "Checking backend health…"
    : health.isSuccess
      ? "Backend connected"
      : "Backend unavailable";

  return (
    <Box component="main" sx={{ minHeight: "100vh", pb: 5 }}>
      <AppBar position="static">
        <Toolbar sx={{ gap: 2 }}>
          <Typography component="h1" variant="h5" sx={{ flexGrow: 1 }}>AiSpace</Typography>
          {currentUser.data && <Typography>{currentUser.data.name}</Typography>}
          {token && <Button color="inherit" onClick={logout}>Log out</Button>}
        </Toolbar>
      </AppBar>
      <Container maxWidth="lg" sx={{ mt: 3 }}>
        <Typography role="status" variant="body2" sx={{ mb: 2 }}>{healthStatus}</Typography>
        {token === null ? (
          <AuthScreen onAuthenticated={setToken} />
        ) : currentUser.isPending ? (
          <Typography role="status">Restoring your session…</Typography>
        ) : currentUser.isError ? (
          <Alert severity="error" action={<Button onClick={logout}>Sign in again</Button>}>
            Your session could not be restored.
          </Alert>
        ) : (
          <>
            <Paper sx={{ mb: 3 }}>
              <Tabs
                value={tab}
                onChange={(_, value: number) => setTab(value)}
                aria-label="Workspace sections"
                variant="scrollable"
                scrollButtons="auto"
              >
                <Tab label="Rooms" />
                <Tab label="Manual booking" />
                <Tab label="AI booking" />
                <Tab label="My bookings" />
              </Tabs>
            </Paper>
            {tab === 0 && <RoomsPanel />}
            {tab === 1 && (
              <Paper sx={{ p: { xs: 2, sm: 3 } }}>
                <Typography component="h2" variant="h5" gutterBottom>Manual booking</Typography>
                {rooms.data && <BookingForm rooms={rooms.data} />}
              </Paper>
            )}
            {tab === 2 && <AIBookingPanel />}
            {tab === 3 && (
              <Paper sx={{ p: { xs: 2, sm: 3 } }}>
                <Typography component="h2" variant="h5" gutterBottom>My bookings</Typography>
                <MyBookings />
              </Paper>
            )}
          </>
        )}
      </Container>
    </Box>
  );
}
