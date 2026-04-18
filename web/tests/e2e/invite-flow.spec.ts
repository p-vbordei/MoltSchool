import { test, expect } from "@playwright/test";

/**
 * Happy path: user lands on /k/<slug>?inv=<token>, sees kindred display name
 * and Claude Code install CTA, clicks Copy, the clipboard contains the
 * correct one-liner.
 *
 * Backend is mocked via Playwright route interception — we don't need a
 * real FastAPI instance for this test.
 */

test("invite landing shows install CTAs and copies Claude Code one-liner", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);

  // Intercept backend kindred-get so the server-side fetch returns our fixture.
  await page.route("**/v1/kindreds/coven", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        slug: "coven",
        display_name: "The Coven",
        description: "witchy things",
        member_count: 4,
      }),
    })
  );

  await page.goto("/k/coven?inv=test-token-123");

  await expect(page.getByRole("heading", { name: "The Coven" })).toBeVisible();
  await expect(page.getByText("/coven")).toBeVisible();
  await expect(page.getByText("Claude Code")).toBeVisible();

  // One-liner is embedded as preformatted text.
  const claudeCmd =
    "curl kindred.sh/install | sh -s -- join test-token-123";
  await expect(page.getByText(claudeCmd)).toBeVisible();

  // Click the first Copy button (the one next to Claude Code).
  const copyButtons = page.getByRole("button", { name: "Copy" });
  await copyButtons.first().click();
  await expect(copyButtons.first()).toHaveText(/Copied!/);

  const clip = await page.evaluate(() => navigator.clipboard.readText());
  expect(clip).toBe(claudeCmd);
});
