import { test, expect } from "@playwright/test";
import { encode } from "@auth/core/jwt";
import { createServer, type Server } from "node:http";

/**
 * Dashboard health page renders 4 indicator sections.
 *
 * Bypasses the OAuth flow by minting a NextAuth v5 session cookie directly
 * (same JWE encoding the server uses) and setting the `kindred-agent-pub`
 * cookie so the backend proxy injects an `x-agent-pubkey` header.
 *
 * The page's server-side fetch goes through the Next proxy route which then
 * calls `${KINDRED_BACKEND_URL}/v1/kindreds/{slug}/health` — here we stand
 * up a real mock HTTP server on port 3199 (the port playwright.config.ts
 * points at) so this test does not require a running FastAPI instance.
 * `page.route(...)` cannot be used here because it only intercepts the
 * browser, not server-side fetches from Next RSC or route handlers.
 */

const BACKEND_PORT = 3199;
const SLUG = "claude-code-patterns";

function mockHealthFixture() {
  return {
    kindred_slug: SLUG,
    generated_at: new Date().toISOString(),
    retrieval_utility: {
      total_asks: 12,
      total_outcomes: 8,
      success_rate: 0.75,
      mean_rank_of_chosen: 1.2,
      top1_precision: 0.5,
    },
    ttfur: {
      sample_size: 3,
      p50_seconds: 42,
      p90_seconds: 180,
    },
    trust_propagation: {
      promoted_artifacts: 2,
      p50_seconds: 3600,
      p90_seconds: 7200,
    },
    staleness_cost: {
      shadow_hits_last_7d: 0,
      expiring_soon_hits_last_7d: 1,
    },
  };
}

let backend: Server;

test.beforeAll(async () => {
  backend = createServer((req, res) => {
    if (req.url === `/v1/kindreds/${SLUG}/health`) {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify(mockHealthFixture()));
      return;
    }
    res.writeHead(404, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: "not_found" }));
  });
  await new Promise<void>((resolve, reject) => {
    backend.once("error", reject);
    backend.listen(BACKEND_PORT, "127.0.0.1", () => resolve());
  });
});

test.afterAll(async () => {
  await new Promise<void>((resolve) => backend.close(() => resolve()));
});

test("dashboard health page renders four indicator sections", async ({
  context,
  page,
  baseURL,
}) => {
  const secret = process.env.NEXTAUTH_SECRET ?? "e2e-insecure-secret";

  // NextAuth v5 salts JWE with the cookie name.
  const now = Math.floor(Date.now() / 1000);
  const sessionToken = await encode({
    token: {
      userId: "github:e2e-user",
      sub: "github:e2e-user",
      name: "e2e",
      email: "e2e@example.com",
      iat: now,
      exp: now + 60 * 60,
    },
    secret,
    salt: "kindred.session-token",
  });

  const baseOrigin = new URL(baseURL ?? "http://localhost:3100");
  await context.addCookies([
    {
      name: "kindred.session-token",
      value: sessionToken,
      domain: baseOrigin.hostname,
      path: "/",
      httpOnly: true,
      sameSite: "Strict",
    },
    {
      name: "kindred-agent-pub",
      value: "ed25519:e2e-test-agent-pub",
      domain: baseOrigin.hostname,
      path: "/",
      sameSite: "Lax",
    },
  ]);

  await page.goto(`${baseURL}/dashboard/${SLUG}/health`);

  await expect(
    page.getByRole("heading", { name: /network health/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /retrieval utility/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /time to first useful retrieval/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /trust propagation/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /staleness cost/i }),
  ).toBeVisible();
});
