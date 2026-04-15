import { expect, test } from "@playwright/test";

test.describe("JOG console (integrated: pi-deck + static build, mock hardware or Pi)", () => {
  test("shell loads: deck root, five controls, log", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("[data-deck-root]")).toBeVisible();
    await expect(page.getByTestId("jog-pad")).toBeVisible();
    /* Four ring sectors are SVG paths with role=button; center is a <button>. ARIA exposure varies by engine. */
    expect(await page.locator("[data-jog-action]").count()).toBe(5);
    await expect(page.getByRole("log")).toBeVisible();
    await expect(page).toHaveTitle(/pi-deck|JOG/i);
  });

  test("websocket connects and first line appears in log", async ({ page }) => {
    await page.goto("/");
    const log = page.getByRole("log");
    await expect(log).toContainText(/connected|control — state=/i, { timeout: 20_000 });
  });

  test("pointer tap Up yields command acceptance in log", async ({ page }) => {
    await page.goto("/");
    await page.locator('[data-jog-action="up"]').click();
    await expect(page.getByRole("log")).toContainText(/hold|release|up/i, { timeout: 15_000 });
  });
});
