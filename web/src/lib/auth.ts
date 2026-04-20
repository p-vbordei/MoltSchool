/**
 * Auth.js (NextAuth v5) configuration.
 *
 * v0 scope: GitHub + Google OAuth, fully wired. Passkey (WebAuthn) is
 * scaffolded as a TODO and not enabled.
 *
 * Google provider activates only when `GOOGLE_ID`/`GOOGLE_SECRET` are set, so
 * deployments without Google creds still boot cleanly with GitHub alone.
 *
 * Self-custody: we no longer mint server-side keypairs. Post-login, a client
 * component (`BootstrapKeys`, mounted in the dashboard) generates Ed25519
 * keypairs in the browser and persists them to IndexedDB. The private key
 * never leaves the browser. The session carries a stable `userId` only so
 * client components can namespace their IDB reads.
 */

import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";
import Google from "next-auth/providers/google";
import { env } from "@/lib/env";

const googleProvider = env.googleId && env.googleSecret
  ? [Google({ clientId: env.googleId, clientSecret: env.googleSecret })]
  : [];

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
    ...googleProvider,
    // TODO(plan-07): Passkey via WebAuthn
    // Passkey({ ... })
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      // Derive a stable user id from the OAuth subject. Used client-side to
      // namespace IndexedDB keypairs (`owner-<userId>`, `agent-<userId>`).
      // No secrets or pubkeys are stashed here — the browser holds those.
      //
      // Fail closed on email: if the provider omits a stable id (`profile.id`
      // from GitHub, `profile.sub` from Google/OIDC), we'd otherwise key the
      // IDB namespace on an email string, which can collide across providers
      // (same email on GitHub + Google -> shared keystore). Keep the namespace
      // bound to the provider's own unforgeable subject.
      if (account && profile) {
        const rawSub = profile.id ?? profile.sub;
        const sub = rawSub != null ? String(rawSub) : "";
        if (sub) token.userId = `${account.provider}:${sub}`;
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
