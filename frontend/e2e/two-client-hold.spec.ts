import { expect, test } from "@playwright/test";

/**
 * Reproduces the multi-tab bug: first browser must not keep data-pressed after another
 * client replaces the hold and releases. Requires pi-deck on baseURL (local e2e backend or Pi).
 */
test.describe("two isolated browser contexts (like two users)", () => {
  test("left sector not stuck after peer replaces hold and releases", async ({ browser, baseURL }) => {
    test.setTimeout(90_000);

    const ctx1 = await browser.newContext();
    const ctx2 = await browser.newContext();
    const page1 = await ctx1.newPage();
    const page2 = await ctx2.newPage();

    const url = baseURL ?? "http://127.0.0.1:8756";
    await page1.goto(url);
    await page2.goto(url);

    const log1 = page1.getByRole("log");
    const log2 = page2.getByRole("log");
    await expect(log1).toContainText(/connected|control — state=/i, { timeout: 25_000 });
    await expect(log2).toContainText(/connected|control — state=/i, { timeout: 25_000 });

    const left1 = page1.getByTestId("jog-pad").locator('[data-jog-action="left"]');
    const left2 = page2.getByTestId("jog-pad").locator('[data-jog-action="left"]');

    /* Client A: start hold on Left (keep mouse down — synthetic dispatchEvent did not run release) */
    const b1 = (await left1.boundingBox())!;
    await page1.mouse.move(b1.x + b1.width / 2, b1.y + b1.height / 2);
    await page1.mouse.down();

    await expect(log1).toContainText(/hold|left/i, { timeout: 15_000 });
    await expect(left1).toHaveAttribute("data-pressed", "true", { timeout: 5_000 });

    /* Client B: same direction replaces A's hold */
    const b2 = (await left2.boundingBox())!;
    await page2.mouse.move(b2.x + b2.width / 2, b2.y + b2.height / 2);
    await page2.mouse.down();
    await expect(log2).toContainText(/hold|left/i, { timeout: 15_000 });

    /* Client B: release — must use real mouse so pointer capture + releasePointer run */
    await page2.mouse.up();
    await expect(log2).toContainText(/release|left/i, { timeout: 15_000 });

    await expect(left1).not.toHaveAttribute("data-pressed", "true", { timeout: 10_000 });

    await ctx1.close();
    await ctx2.close();
  });
});
