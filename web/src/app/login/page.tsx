import Link from "next/link";
import { signIn } from "@/lib/auth";
import { env } from "@/lib/env";

export default function LoginPage() {
  async function githubSignIn() {
    "use server";
    await signIn("github", { redirectTo: "/dashboard" });
  }

  async function googleSignIn() {
    "use server";
    await signIn("google", { redirectTo: "/dashboard" });
  }

  const googleEnabled = Boolean(env.googleId && env.googleSecret);

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-6 py-16">
      <Link
        href="/"
        className="mb-12 font-serif text-2xl tracking-tight text-foreground"
      >
        Kindred
      </Link>

      <div className="grimoire-border w-full rounded-lg p-8">
        <h1 className="font-serif text-2xl">Sign in to your notebook</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          See the notebooks you&apos;re part of and the pages your team has shared.
        </p>

        <form action={githubSignIn} className="mt-8">
          <button
            type="submit"
            className="flex w-full items-center justify-center gap-2 rounded-md bg-foreground px-4 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-90"
          >
            Continue with GitHub
          </button>
        </form>

        <div className="mt-6 space-y-2 text-xs text-muted-foreground">
          {googleEnabled ? (
            <form action={googleSignIn}>
              <button
                type="submit"
                className="flex w-full items-center justify-center gap-2 rounded-md border border-border px-4 py-2 text-foreground transition-colors hover:bg-muted"
              >
                Continue with Google
              </button>
            </form>
          ) : (
            <button
              type="button"
              disabled
              className="flex w-full cursor-not-allowed items-center justify-center gap-2 rounded-md border border-border px-4 py-2 opacity-50"
            >
              Google — coming soon
            </button>
          )}
          <button
            type="button"
            disabled
            className="flex w-full cursor-not-allowed items-center justify-center gap-2 rounded-md border border-border px-4 py-2 opacity-50"
          >
            Passkey — coming soon
          </button>
        </div>
      </div>

      <p className="mt-8 text-xs text-muted-foreground">
        No trackers, no analytics. Your keys live only in your session.
      </p>
    </main>
  );
}
