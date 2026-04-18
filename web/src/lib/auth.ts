/**
 * Auth.js (NextAuth v5) configuration.
 *
 * v0 scope: GitHub OAuth only, fully wired. Google + Passkey (WebAuthn) are
 * scaffolded as TODOs and not enabled.
 *
 * Self-custody: we no longer mint server-side keypairs. Post-login, a client
 * component (`BootstrapKeys`, mounted in the dashboard) generates Ed25519
 * keypairs in the browser and persists them to IndexedDB. The private key
 * never leaves the browser. The session carries a stable `userId` only so
 * client components can namespace their IDB reads.
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
      // Derive a stable user id from the OAuth subject. Used client-side to
      // namespace IndexedDB keypairs (`owner-<userId>`, `agent-<userId>`).
      // No secrets or pubkeys are stashed here — the browser holds those.
      if (account && profile) {
        const sub = String(profile.id ?? profile.sub ?? profile.email ?? "");
        if (sub) token.userId = sub;
      }
      return token;
    },
    async session({ session, token }) {
      if (token.userId) {
        (session as { userId?: string }).userId = token.userId as string;
        if (session.user) {
          (session.user as { id?: string }).id = token.userId as string;
        }
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
