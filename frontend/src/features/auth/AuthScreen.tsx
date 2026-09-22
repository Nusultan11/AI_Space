import { zodResolver } from "@hookform/resolvers/zod";
import { Alert, Box, Button, Paper, Tab, Tabs, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { ApiError, api } from "../../api/client";
import { setAccessToken } from "../../auth/session";
import {
  loginSchema,
  registerSchema,
  type LoginValues,
  type RegisterValues,
} from "./authSchema";

interface AuthScreenProps {
  onAuthenticated: (token: string) => void;
}

export function AuthScreen({ onAuthenticated }: AuthScreenProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const login = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });
  const register = useForm<RegisterValues>({ resolver: zodResolver(registerSchema) });

  async function completeLogin(values: LoginValues) {
    const response = await api.login(values);
    setAccessToken(response.access_token);
    onAuthenticated(response.access_token);
  }

  const submitLogin = login.handleSubmit(async (values) => {
    setError(null);
    try {
      await completeLogin(values);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Sign in failed.");
    }
  });

  const submitRegister = register.handleSubmit(async (values) => {
    setError(null);
    try {
      await api.register(values);
      await completeLogin({ email: values.email, password: values.password });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Registration failed.");
    }
  });

  return (
    <Paper sx={{ maxWidth: 440, mx: "auto", p: { xs: 2, sm: 4 } }}>
      <Tabs
        value={mode}
        onChange={(_, value: "login" | "register") => {
          setMode(value);
          setError(null);
        }}
        aria-label="Authentication mode"
        variant="fullWidth"
      >
        <Tab value="login" label="Sign in" />
        <Tab value="register" label="Register" />
      </Tabs>
      <Box
        component="form"
        onSubmit={mode === "login" ? submitLogin : submitRegister}
        sx={{ display: "grid", gap: 2, mt: 3 }}
      >
        <Typography component="h2" variant="h5">
          {mode === "login" ? "Welcome back" : "Create your account"}
        </Typography>
        {error && <Alert severity="error">{error}</Alert>}
        {mode === "register" && (
          <TextField
            label="Name"
            autoComplete="name"
            {...register.register("name")}
            error={Boolean(register.formState.errors.name)}
            helperText={register.formState.errors.name?.message}
          />
        )}
        {mode === "login" ? (
          <>
            <TextField
              label="Email"
              type="email"
              autoComplete="email"
              {...login.register("email")}
              error={Boolean(login.formState.errors.email)}
              helperText={login.formState.errors.email?.message}
            />
            <TextField
              label="Password"
              type="password"
              autoComplete="current-password"
              {...login.register("password")}
              error={Boolean(login.formState.errors.password)}
              helperText={login.formState.errors.password?.message}
            />
          </>
        ) : (
          <>
            <TextField
              label="Email"
              type="email"
              autoComplete="email"
              {...register.register("email")}
              error={Boolean(register.formState.errors.email)}
              helperText={register.formState.errors.email?.message}
            />
            <TextField
              label="Password"
              type="password"
              autoComplete="new-password"
              {...register.register("password")}
              error={Boolean(register.formState.errors.password)}
              helperText={register.formState.errors.password?.message}
            />
          </>
        )}
        <Button
          type="submit"
          variant="contained"
          disabled={login.formState.isSubmitting || register.formState.isSubmitting}
        >
          {mode === "login" ? "Sign in" : "Create account"}
        </Button>
      </Box>
    </Paper>
  );
}
