import { expect, test, type Page } from "@playwright/test";

async function register(page: Page, suffix: string) {
  await page.goto("/");
  await page.getByRole("tab", { name: "Register" }).click();
  await page.getByLabel("Name").fill("Playwright User");
  await page.getByLabel("Email").fill(`manual-${suffix}@example.com`);
  await page.getByLabel("Password").fill("playwright-password");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("tab", { name: "Rooms" })).toBeVisible();
}

function futureDate(days: number): string {
  const value = new Date();
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

test("registers, books manually, lists the booking, and offers conflict alternatives", async ({
  page,
}) => {
  const suffix = Date.now().toString();
  await register(page, suffix);
  await expect(page.getByText("Большая переговорная")).toBeVisible();

  const date = futureDate(21 + (Date.now() % 20));
  const minute = String(Date.now() % 30).padStart(2, "0");
  const start = `10:${minute}`;
  const end = `11:${minute}`;
  const title = `Manual journey ${suffix}`;

  await page.getByRole("tab", { name: "Manual booking" }).click();
  await page.getByLabel("Date").fill(date);
  await page.getByLabel("Start time").fill(start);
  await page.getByLabel("End time").fill(end);
  await page.getByLabel("Meeting title").fill(title);
  await page.getByRole("button", { name: "Create booking" }).click();
  await expect(page.getByText("Booking confirmed.")).toBeVisible();

  await page.getByRole("tab", { name: "My bookings" }).click();
  await expect(page.getByRole("heading", { name: title })).toBeVisible();

  await page.getByRole("tab", { name: "Manual booking" }).click();
  await page.getByLabel("Date").fill(date);
  await page.getByLabel("Start time").fill(start);
  await page.getByLabel("End time").fill(end);
  await page.getByLabel("Meeting title").fill(`Overlap ${suffix}`);
  await page.getByRole("button", { name: "Create booking" }).click();

  await expect(page.getByText("The room is already booked for this time.")).toBeVisible();
  await expect(page.getByText("Choose an alternative, then submit again")).toBeVisible();
  await expect(page.getByRole("button", { name: /^Use / }).first()).toBeVisible();
});
