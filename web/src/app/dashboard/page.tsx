import { redirect } from "next/navigation";
import Link from "next/link";
import { auth, signOut } from "@/lib/auth";
import { backend, BackendError } from "@/lib/backend";
import { KindredList } from "@/components/kindred-list";
import { BootstrapKeys } from "@/components/bootstrap-keys";

export const dynamic = "force-dynamic";

export default async function Dashboard() {
  const session = await auth();
  if (!session) redirect("/login");

  let kindreds: Awaited<ReturnType<typeof backend.kindreds.list>>["kindreds"] =
    [];
  try {
    const resp = await backend.kindreds.list();
    kindreds = resp.kindreds ?? [];
  } catch (err) {
    if (!(err instanceof BackendError) || err.status !== 404) {
      // Log but render empty state — don't 500 the dashboard for a flaky list.
      console.error("[dashboard] list kindreds failed", err);
    }
  }

  async function handleSignOut() {
    "use server";
    await signOut({ redirectTo: "/" });
  }

  const userName =
    session.user?.name ?? session.user?.email ?? "friend";
  const userId =
    (session as { userId?: string }).userId ??
    session.user?.email ??
    session.user?.name ??
    "";

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-6 py-12">
      {userId && (
        <BootstrapKeys
          userId={userId}
          email={session.user?.email}
          displayName={session.user?.name}
        />
      )}
      <header className="flex items-center justify-between">
        <Link href="/" className="font-serif text-xl tracking-tight">
          Kindred
        </Link>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-muted-foreground">{userName}</span>
          <form action={handleSignOut}>
            <button
              type="submit"
              className="rounded-md border border-border px-3 py-1.5 text-xs hover:border-accent"
            >
              Sign out
            </button>
          </form>
        </div>
      </header>

      <section className="mt-12">
        <div className="flex items-end justify-between">
          <h1 className="font-serif text-3xl">Your kindreds</h1>
          <button
            type="button"
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90"
            disabled
            title="Create via CLI for v0"
          >
            Create kindred
          </button>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          Every kindred is a private, append-only grimoire. Share invite links
          to add friends; revoke any time.
        </p>

        <div className="mt-8">
          <KindredList kindreds={kindreds} />
        </div>
      </section>
    </main>
  );
}
