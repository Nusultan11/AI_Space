import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

async function register(page: Page, suffix: string) {
  await page.goto("/");
  await page.getByRole("tab", { name: "Register" }).click();
  await page.getByLabel("Name").fill("AI Playwright User");
  await page.getByLabel("Email").fill(`ai-${suffix}@example.com`);
  await page.getByLabel("Password").fill("playwright-password");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("tab", { name: "Rooms" })).toBeVisible();
}

interface FreeIntentInterval {
  room: { id: string; name: string };
  startAt: string;
  endAt: string;
}

async function findFreeInterval(
  request: APIRequestContext,
  token: string,
): Promise<FreeIntentInterval> {
  for (let offset = 60; offset < 140; offset += 1) {
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
    if (room) {
      return {
        room: { id: room.room_id, name: room.name },
        startAt: start.toISOString(),
        endAt: end.toISOString(),
      };
    }
  }
  throw new Error("No free future interval was found");
}

test("AI preview confirms through the real normal booking endpoint", async ({ page, request }) => {
  const suffix = Date.now().toString();
  await register(page, suffix);
  const token = await page.evaluate(() => sessionStorage.getItem("aispace.access-token"));
  if (!token) throw new Error("Authentication token was not stored");
  const interval = await findFreeInterval(request, token);
  const room = interval.room;
  const title = `AI journey ${suffix}`;
  const editedTitle = `Edited AI journey ${suffix}`;

  await page.route("**/api/v1/ai/booking-intent", async (route) => {
    expect(route.request().method()).toBe("POST");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        room_id: room.id,
        room_reference: room.name,
        start_at: interval.startAt,
        end_at: interval.endAt,
        title,
        participants_count: 2,
        needs_clarification: false,
        missing_fields: [],
        clarification_message: null,
      }),
    });
  });

  await page.getByRole("tab", { name: "AI booking" }).click();
  await page.getByLabel("Meeting request").fill("Book a planning session tomorrow");
  await page.getByRole("button", { name: "Prepare preview" }).click();
  await expect(page.getByRole("heading", { name: "Review AI preview" })).toBeVisible();
  await expect(page.getByLabel("Meeting title")).toHaveValue(title);
  await page.getByLabel("Meeting title").fill(editedTitle);

  const bookingResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/bookings") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Confirm booking" }).click();
  const persisted = await bookingResponse;
  expect(persisted.status()).toBe(201);
  expect(persisted.request().postDataJSON()).toMatchObject({
    title: editedTitle,
    room_id: room.id,
  });
  await expect(page.getByText("Booking confirmed.")).toBeVisible();

  await page.getByRole("tab", { name: "My bookings" }).click();
  await expect(page.getByRole("heading", { name: editedTitle })).toBeVisible();
});
