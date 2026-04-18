import { defineConfig, devices } from "@playwright/test";

/**
 * Single happy-path e2e for the invite landing page.
 *
 * Opt-in only — CI skips unless PLAYWRIGHT=1 is set, because the test
 * launches a full Next dev server + mocks backend responses via a test
 * server. Plan 07 will add a proper invite-flow matrix.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3100",
    trace: "off",
    headless: true,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "npm run start",
    port: 3100,
    env: {
      PORT: "3100",
      KINDRED_BACKEND_URL: "http://localhost:3199",
      NEXTAUTH_SECRET: "e2e-insecure-secret",
      NEXTAUTH_URL: "http://localhost:3100",
      NODE_ENV: "production",
    },
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
