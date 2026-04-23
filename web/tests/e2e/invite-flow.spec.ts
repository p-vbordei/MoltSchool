import { test, expect } from "@playwright/test";
import { createServer, type Server } from "node:http";

/**
 * Happy path: user lands on /k/<slug>?inv=<token>, sees kindred display name
 * and Claude Code install CTA, clicks Copy, the clipboard contains the
 * correct one-liner.
 *
 * The /k/[slug] route is a React Server Component that fetches the kindred
 * server-side, so Playwright's page.route() (browser-only) cannot intercept
 * it. We stand up a real HTTP server on the port the Next server is
 * configured to call (KINDRED_BACKEND_URL=http://localhost:3199).
 */

let server: Server;

test.beforeAll(async () => {
  server = createServer((req, res) => {
    if (req.method === "GET" && req.url === "/v1/kindreds/coven") {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(
        JSON.stringify({
          slug: "coven",
          display_name: "The Coven",
          description: "witchy things",
          member_count: 4,
        })
      );
      return;
    }
    res.writeHead(404);
    res.end();
  });
  await new Promise<void>((resolve) => server.listen(3199, "127.0.0.1", resolve));
});

test.afterAll(async () => {
  await new Promise<void>((resolve, reject) =>
    server.close((err) => (err ? reject(err) : resolve()))
  );
});

test("invite landing shows install CTAs and copies Claude Code one-liner", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);

  await page.goto("/k/coven?inv=test-token-123");

  await expect(page.getByRole("heading", { name: "The Coven" })).toBeVisible();
  await expect(page.getByText("/coven · 4 members")).toBeVisible();
  await expect(page.getByText("Claude Code")).toBeVisible();

  // One-liner is embedded as preformatted text.
  const claudeCmd =
    "curl kindred.sh/install | sh -s -- join test-token-123";
  await expect(page.getByText(claudeCmd)).toBeVisible();

  // Click the first Copy button (the one next to Claude Code). Use a stable
  // positional locator — by-name filtering would drift off button 1 once it
  // flips to "Copied!" and then match the CLI card instead.
  const claudeCopyBtn = page.locator("button").first();
  await claudeCopyBtn.click();
  await expect(claudeCopyBtn).toHaveText(/Copied!/);

  const clip = await page.evaluate(() => navigator.clipboard.readText());
  expect(clip).toBe(claudeCmd);
});
