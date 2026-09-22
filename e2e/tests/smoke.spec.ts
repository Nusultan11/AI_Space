import { expect, test } from "@playwright/test";

test("serves the SPA and proxies backend health", async ({ page, request }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "AiSpace" })).toBeVisible();
  await expect(page.getByRole("status")).toHaveText("Backend connected");

  const live = await request.get("/api/v1/health/live");
  expect(live.ok()).toBe(true);
  expect(await live.json()).toEqual({ status: "ok" });

  const ready = await request.get("/api/v1/health/ready");
  expect(ready.ok()).toBe(true);
  expect(await ready.json()).toEqual({ status: "ready" });
});
