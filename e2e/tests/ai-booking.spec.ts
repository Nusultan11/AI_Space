import { expect, test, type Page } from "@playwright/test";

async function register(page: Page, suffix: string) {
  await page.goto("/");
  await page.getByRole("tab", { name: "Register" }).click();
  await page.getByLabel("Name").fill("AI Playwright User");
  await page.getByLabel("Email").fill(`ai-${suffix}@example.com`);
  await page.getByLabel("Password").fill("playwright-password");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("tab", { name: "Rooms" })).toBeVisible();
}

function futureDate(days: number): string {
  const value = new Date();
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

test("AI preview confirms through the real normal booking endpoint", async ({ page, request }) => {
  const suffix = Date.now().toString();
  await register(page, suffix);
  const token = await page.evaluate(() => sessionStorage.getItem("aispace.access-token"));
  expect(token).toBeTruthy();
  const roomsResponse = await request.get("/api/v1/rooms", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(roomsResponse.ok()).toBe(true);
  const rooms = (await roomsResponse.json()) as Array<{ id: string; name: string }>;
  const room = rooms[0];
  const date = futureDate(50 + (Date.now() % 20));
  const title = `AI journey ${suffix}`;

  await page.route("**/api/v1/ai/booking-intent", async (route) => {
    expect(route.request().method()).toBe("POST");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        room_id: room.id,
        room_reference: room.name,
        start_at: `${date}T10:00:00Z`,
        end_at: `${date}T11:00:00Z`,
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

  const bookingResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/bookings") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Confirm booking" }).click();
  const persisted = await bookingResponse;
  expect(persisted.status()).toBe(201);
  expect(persisted.request().postDataJSON()).toMatchObject({ title, room_id: room.id });
  await expect(page.getByText("Booking confirmed.")).toBeVisible();

  await page.getByRole("tab", { name: "My bookings" }).click();
  await expect(page.getByRole("heading", { name: title })).toBeVisible();
});
