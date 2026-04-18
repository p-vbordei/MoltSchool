import { redirect } from "next/navigation";
import Link from "next/link";
import { auth } from "@/lib/auth";
import { backend, type AuditEvent } from "@/lib/backend";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ slug: string }> };

export default async function RollbackPage({ params }: Props) {
  const session = await auth();
  if (!session) redirect("/login");
  const { slug } = await params;

  let events: AuditEvent[] = [];
  try {
    const resp = await backend.audit.list(slug);
    events = resp.events ?? [];
  } catch (err) {
    console.error("[rollback] list failed", err);
  }

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-6 py-12">
      <nav className="mb-8 text-sm">
        <Link
          href={`/dashboard/${slug}`}
          className="text-muted-foreground hover:text-foreground"
        >
          ← Back to {slug}
        </Link>
      </nav>
      <header className="border-b border-border pb-6">
        <h1 className="font-serif text-3xl tracking-tight">Rollback</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Revert the kindred to a prior sequence number. This is a privileged
          action: it emits a new signed rollback event and is itself append-
          only (you can roll forward again).
        </p>
      </header>

      <section className="mt-8">
        {events.length === 0 ? (
          <div className="grimoire-border rounded-lg p-8 text-center text-muted-foreground">
            No rollback points available.
          </div>
        ) : (
          <ol className="grimoire-border divide-y divide-border rounded-lg">
            {events.map((e) => (
              <li
                key={e.seq}
                className="flex items-center justify-between gap-4 p-4 text-sm"
              >
                <div className="min-w-0 flex-1">
                  <div className="font-mono text-xs text-muted-foreground">
                    #{e.seq} · {e.ts}
                  </div>
                  <div className="mt-1 truncate text-foreground">
                    {e.action}
                    {e.agent && (
                      <span className="ml-2 font-mono text-xs text-muted-foreground">
                        by {e.agent}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  disabled
                  title="Rollback execution wired to backend — UI action deferred to Plan 07 polish"
                  className="shrink-0 cursor-not-allowed rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground opacity-60"
                >
                  Revert to here
                </button>
              </li>
            ))}
          </ol>
        )}
      </section>
    </main>
  );
}
