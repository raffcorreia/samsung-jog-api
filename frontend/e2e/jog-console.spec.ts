import { expect, test } from "@playwright/test";

test.describe("JOG console (integrated: pi-deck + static build, mock hardware or Pi)", () => {
  test("shell loads: hero, status, five controls, log", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /JOG console/i })).toBeVisible();
    await expect(page.getByText(/Samsung CJ791/i)).toBeVisible();
    await expect(page.getByRole("status")).toBeVisible();
    await expect(page.getByTestId("jog-pad")).toBeVisible();
    expect(await page.getByRole("button").count()).toBe(5);
    await expect(page.getByRole("log")).toBeVisible();
  });

  test("websocket connects and first line appears in log", async ({ page }) => {
    await page.goto("/");
    const log = page.getByRole("log");
    await expect(log).toContainText(/connected|control — state=/i, { timeout: 20_000 });
    await expect(page.getByTestId("ws-status")).toHaveAttribute("data-live", "true", { timeout: 20_000 });
  });

  test("pointer tap Up yields command acceptance in log", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Up" }).click();
    await expect(page.getByRole("log")).toContainText(/command ok|accepted|up/i, { timeout: 15_000 });
  });
});
