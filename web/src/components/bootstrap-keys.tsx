"use client";

/**
 * On first post-login visit, bootstrap the user's owner + agent keypairs
 * client-side in IndexedDB, then register them with the backend.
 *
 * Why client-side: the private key must never leave the browser, otherwise
 * the server can impersonate the user (residual risk R2). This component
 * replaces the v0 server-side stub (pk_owner_<sub>) with real Ed25519.
 *
 * Flow on first mount:
 *   1. If no owner keypair for this user, generate + save + POST /users.
 *   2. If no agent keypair, generate + save, sign the attestation with the
 *      owner sk, POST /users/<id>/agents.
 *   3. Idempotent — subsequent mounts no-op.
 *
 * Failures are logged but swallowed: the dashboard still renders. A user
 * whose bootstrap fails will retry on next visit.
 */

import { useEffect, useRef } from "react";
import {
  canonicalJson,
  generateKeypair,
  hex,
  pubkeyToStr,
  sign,
} from "@/lib/crypto/keys";
import { loadKeypair, saveKeypair } from "@/lib/crypto/keystore";

type Props = {
  userId: string;
  email?: string | null;
  displayName?: string | null;
};

const SCOPE: { kindreds: string[]; actions: string[] } = {
  kindreds: ["*"],
  actions: ["read", "contribute"],
};
const AGENT_TTL_DAYS = 180;

export function BootstrapKeys({ userId, email, displayName }: Props) {
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    (async () => {
      try {
        await bootstrap({ userId, email, displayName });
      } catch (err) {
        // Non-fatal: dashboard still works for read-only flows. Sign/bless
        // will re-error more loudly when the user tries to act.
        console.error("[bootstrap-keys] failed", err);
      }
    })();
  }, [userId, email, displayName]);

  return null;
}

/**
 * Mirror public keys into non-httpOnly cookies so the RSC-side proxy
 * (/api/backend/[...path]/route.ts) can forward them as x-owner-pubkey /
 * x-agent-pubkey headers to the backend. Only the public halves leave the
 * browser; the private halves stay in IndexedDB.
 */
function setPubCookie(name: string, value: string) {
  // SameSite=Strict mirrors the session cookie. 30-day TTL matches the agent
  // attestation refresh cadence loosely; bootstrap re-runs on expiry.
  const maxAge = 60 * 60 * 24 * 30;
  const secure = location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${maxAge}; SameSite=Strict${secure}`;
}

async function bootstrap(opts: {
  userId: string;
  email?: string | null;
  displayName?: string | null;
}): Promise<void> {
  const ownerId = `owner-${opts.userId}`;
  const agentId = `agent-${opts.userId}`;

  let owner = await loadKeypair(ownerId);
  if (!owner) {
    const { sk, pk } = await generateKeypair();
    await saveKeypair(ownerId, sk, pk);
    owner = { sk, pk };
    // Register the user with their real pubkey. If the backend already
    // knows this pubkey (409) we ignore; if it doesn't and we fail here,
    // subsequent /users/by-pubkey lookups will 404 and we'll retry next time.
    const resp = await fetch("/api/backend/users", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        email: opts.email ?? undefined,
        display_name: opts.displayName ?? opts.email ?? "kindred user",
        pubkey: pubkeyToStr(pk),
      }),
    });
    if (!resp.ok && resp.status !== 409) {
      console.warn("[bootstrap-keys] /users register failed", resp.status);
    }
  }
  setPubCookie("kindred-owner-pub", pubkeyToStr(owner.pk));

  const existingAgent = await loadKeypair(agentId);
  if (existingAgent) {
    setPubCookie("kindred-agent-pub", pubkeyToStr(existingAgent.pk));
    return;
  }

  const { sk: agentSk, pk: agentPk } = await generateKeypair();
  await saveKeypair(agentId, agentSk, agentPk);

  const expiresAt = new Date(
    Date.now() + AGENT_TTL_DAYS * 24 * 3600 * 1000
  ).toISOString();
  const payload = {
    agent_pubkey: pubkeyToStr(agentPk),
    scope: SCOPE,
    expires_at: expiresAt,
  };
  const canonical = canonicalJson(payload);
  const sig = await sign(owner.sk, canonical);

  const userResp = await fetch(
    `/api/backend/users/by-pubkey/${encodeURIComponent(pubkeyToStr(owner.pk))}`
  );
  if (!userResp.ok) {
    console.warn("[bootstrap-keys] owner lookup failed", userResp.status);
    return;
  }
  const userRow = (await userResp.json()) as { id: string };

  const agentResp = await fetch(
    `/api/backend/users/${userRow.id}/agents`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        agent_pubkey: pubkeyToStr(agentPk),
        display_name: "web-agent",
        scope: SCOPE,
        expires_at: expiresAt,
        sig: hex(sig),
      }),
    }
  );
  if (!agentResp.ok && agentResp.status !== 409) {
    console.warn("[bootstrap-keys] agent register failed", agentResp.status);
    return;
  }
  setPubCookie("kindred-agent-pub", pubkeyToStr(agentPk));
}
