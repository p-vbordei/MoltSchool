/**
 * Central env var access with sane defaults.
 * Server-only — do not import in client components.
 */

export const env = {
  backendUrl: process.env.KINDRED_BACKEND_URL ?? "http://localhost:8000",
  nextAuthSecret: process.env.NEXTAUTH_SECRET ?? "",
  githubId: process.env.GITHUB_ID ?? "",
  githubSecret: process.env.GITHUB_SECRET ?? "",
  googleId: process.env.GOOGLE_ID ?? "",
  googleSecret: process.env.GOOGLE_SECRET ?? "",
};
