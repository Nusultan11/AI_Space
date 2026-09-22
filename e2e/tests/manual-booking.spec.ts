import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

async function register(page: Page, suffix: string) {
  await page.goto("/");
  await page.getByRole("tab", { name: "Register" }).click();
  await page.getByLabel("Name").fill("Playwright User");
  await page.getByLabel("Email").fill(`manual-${suffix}@example.com`);
  await page.getByLabel("Password").fill("playwright-password");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("tab", { name: "Rooms" })).toBeVisible();
}

interface FreeInterval {
  roomId: string;
  roomName: string;
  date: string;
  startTime: string;
  endTime: string;
}

function localInput(iso: string, timezone: string): { date: string; time: string } {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    })
      .formatToParts(new Date(iso))
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value]),
  );
  return {
    date: `${parts.year}-${parts.month}-${parts.day}`,
    time: `${parts.hour}:${parts.minute}`,
  };
}

async function findFreeInterval(
  request: APIRequestContext,
  token: string,
): Promise<FreeInterval> {
  for (let offset = 14; offset < 90; offset += 1) {
    const start = new Date();
    start.setUTCDate(start.getUTCDate() + offset);
    start.setUTCHours(6 + (offset % 8), 0, 0, 0);
    const end = new Date(start.getTime() + 60 * 60 * 1000);
    const availability = await request.get(
      `/api/v1/availability?start_at=${encodeURIComponent(start.toISOString())}&end_at=${encodeURIComponent(end.toISOString())}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    expect(availability.ok()).toBe(true);
    const body = (await availability.json()) as {
      rooms: Array<{ room_id: string; name: string }>;
    };
    const room = body.rooms[0];
    if (!room) continue;
    const schedule = await request.get(
      `/api/v1/rooms/${room.room_id}/schedule?date=${start.toISOString().slice(0, 10)}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    expect(schedule.ok()).toBe(true);
    const timezone = ((await schedule.json()) as { timezone: string }).timezone;
    const localStart = localInput(start.toISOString(), timezone);
    const localEnd = localInput(end.toISOString(), timezone);
    return {
      roomId: room.room_id,
      roomName: room.name,
      date: localStart.date,
      startTime: localStart.time,
      endTime: localEnd.time,
    };
  }
  throw new Error("No free future interval was found");
}

test("registers, books manually, lists the booking, and offers conflict alternatives", async ({
  page,
  request,
}) => {
  const suffix = Date.now().toString();
  await register(page, suffix);
  await expect(page.getByText("Большая переговорная")).toBeVisible();
  const token = await page.evaluate(() => sessionStorage.getItem("aispace.access-token"));
  if (!token) throw new Error("Authentication token was not stored");
  const interval = await findFreeInterval(request, token);
  const title = `Manual journey ${suffix}`;

  await page.getByRole("tab", { name: "Manual booking" }).click();
  await page.getByLabel("Room").click();
  await page.getByRole("option").filter({ hasText: interval.roomName }).click();
  await page.getByLabel("Date").fill(interval.date);
  await page.getByLabel("Start time").fill(interval.startTime);
  await page.getByLabel("End time").fill(interval.endTime);
  await page.getByLabel("Meeting title").fill(title);
  await page.getByRole("button", { name: "Create booking" }).click();
  await expect(page.getByText("Booking confirmed.")).toBeVisible();

  await page.getByRole("tab", { name: "My bookings" }).click();
  await expect(page.getByRole("heading", { name: title })).toBeVisible();

  await page.getByRole("tab", { name: "Manual booking" }).click();
  await page.getByLabel("Room").click();
  await page.getByRole("option").filter({ hasText: interval.roomName }).click();
  await page.getByLabel("Date").fill(interval.date);
  await page.getByLabel("Start time").fill(interval.startTime);
  await page.getByLabel("End time").fill(interval.endTime);
  await page.getByLabel("Meeting title").fill(`Overlap ${suffix}`);
  await page.getByRole("button", { name: "Create booking" }).click();

  await expect(page.getByText("The room is already booked for this time.")).toBeVisible();
  await expect(page.getByText("Choose an alternative, then submit again")).toBeVisible();
  await expect(page.getByRole("button", { name: /^Use / }).first()).toBeVisible();
});
