/**
 * Auth.js (NextAuth v5) configuration.
 *
 * v0 scope: GitHub OAuth only, fully wired. Google + Passkey (WebAuthn) are
 * scaffolded as TODOs and not enabled — they require additional provider
 * setup (Google Cloud project, WebAuthn challenge/response storage) that we
 * defer to Plan 07.
 *
 * Keystore tradeoff (documented in README): on first GitHub login we
 * generate owner + agent keypairs server-side, encrypt with NEXTAUTH_SECRET,
 * and stash them in the JWT. This sacrifices self-custody for a single-
 * click onboarding. Plan 07 migrates to client-side WebCrypto.
 */

import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";
import { env } from "@/lib/env";

export const { handlers, signIn, signOut, auth } = NextAuth({
  trustHost: true,
  secret: env.nextAuthSecret || "dev-only-insecure-secret-change-me",
  session: {
    strategy: "jwt",
    maxAge: 60 * 60 * 24 * 7, // 7 days
  },
  cookies: {
    sessionToken: {
      name: "kindred.session-token",
      options: {
        httpOnly: true,
        sameSite: "strict",
        path: "/",
        secure: process.env.NODE_ENV === "production",
      },
    },
  },
  providers: [
    GitHub({
      clientId: env.githubId,
      clientSecret: env.githubSecret,
    }),
    // TODO(plan-07): Google provider
    // Google({ clientId: env.googleId, clientSecret: env.googleSecret }),
    // TODO(plan-07): Passkey via WebAuthn
    // Passkey({ ... })
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      // On first login: mint owner + agent pubkeys (stub for v0 — real impl
      // generates Ed25519 via WebCrypto on server and encrypts private halves
      // with NEXTAUTH_SECRET before storing). For now we derive deterministic
      // placeholders from the OAuth subject so the proxy has something to
      // forward. Plan 07 replaces with real keygen.
      if (account && profile) {
        const sub = String(profile.id ?? profile.sub ?? profile.email ?? "");
        token.ownerPubkey = `pk_owner_${sub}`;
        token.agentPubkey = `pk_agent_${sub}`;
      }
      return token;
    },
    async session({ session, token }) {
      if (token.ownerPubkey) {
        (session as { ownerPubkey?: string }).ownerPubkey =
          token.ownerPubkey as string;
      }
      if (token.agentPubkey) {
        (session as { agentPubkey?: string }).agentPubkey =
          token.agentPubkey as string;
      }
      return session;
    },
    async redirect({ url, baseUrl }) {
      // Open-redirect guard: only allow same-origin callbacks.
      if (url.startsWith("/")) return `${baseUrl}${url}`;
      try {
        const parsed = new URL(url);
        if (parsed.origin === baseUrl) return url;
      } catch {
        /* fall through */
      }
      return `${baseUrl}/dashboard`;
    },
  },
  pages: {
    signIn: "/login",
  },
});
