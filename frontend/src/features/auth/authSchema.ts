import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

export const registerSchema = loginSchema.extend({
  name: z.string().trim().min(1, "Name is required.").max(100),
  password: z.string().min(8, "Use at least 8 characters.").max(128),
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
