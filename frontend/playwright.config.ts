import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig, devices } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");
const backendScript = path.join(__dirname, "scripts", "e2e-backend.sh");

/**
 * Local runs: Playwright hits pi-deck on 8756 (same origin as API + `/ws/events` — no Vite proxy).
 * Set E2E_BASE_URL to skip starting the local backend, e.g.:
 *   E2E_BASE_URL=http://<deck-host-ip>:8756 npm run test:e2e
 */
const remoteBase = process.env.E2E_BASE_URL?.replace(/\/$/, "") ?? "";
const useRemote = remoteBase.length > 0;

export default defineConfig({
  testDir: "e2e",
  workers: process.env.CI ? 2 : undefined,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: useRemote ? remoteBase : "http://127.0.0.1:8756",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: useRemote
    ? undefined
    : {
        command: `bash "${backendScript}"`,
        cwd: repoRoot,
        url: "http://127.0.0.1:8756/health",
        timeout: 120_000,
        reuseExistingServer: !process.env.CI,
      },
});
