/**
 * Server-side session helpers.
 *
 * v0 keystore tradeoff: owner + agent keypairs are generated server-side on
 * first login and encrypted at rest with NEXTAUTH_SECRET. This sacrifices
 * self-custody for UX simplicity (no WebAuthn unlock prompt per action). Plan
 * 07 follow-up: migrate to client-side WebCrypto with passkey-wrapped keys.
 */

import { cookies } from "next/headers";

export type SessionKeys = {
  ownerPubkey?: string;
  agentPubkey?: string;
};

/**
 * Returns the caller's public keys if they have a session.
 *
 * For v0 we read pubkeys out of the Auth.js JWT claims (which the route
 * handler populates at login time). Returns null if no session exists —
 * the proxy then forwards unauthenticated, and the backend will 401 any
 * protected endpoint.
 */
export async function getSessionKeys(): Promise<SessionKeys | null> {
  try {
    const jar = await cookies();
    const ownerPubkey = jar.get("kindred-owner-pub")?.value;
    const agentPubkey = jar.get("kindred-agent-pub")?.value;
    if (!ownerPubkey && !agentPubkey) return null;
    return { ownerPubkey, agentPubkey };
  } catch {
    return null;
  }
}
