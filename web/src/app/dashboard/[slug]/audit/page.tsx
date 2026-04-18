import { redirect } from "next/navigation";
import Link from "next/link";
import { auth } from "@/lib/auth";
import { backend, type AuditEvent } from "@/lib/backend";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ slug: string }> };

export default async function AuditPage({ params }: Props) {
  const session = await auth();
  if (!session) redirect("/login");
  const { slug } = await params;

  let events: AuditEvent[] = [];
  try {
    const resp = await backend.audit.list(slug);
    events = resp.events ?? [];
  } catch (err) {
    console.error("[audit] list failed", err);
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
        <h1 className="font-serif text-3xl tracking-tight">Audit log</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Append-only history of actions on this kindred, newest first. Every
          row is cryptographically linked to the row before it.
        </p>
      </header>

      <section className="mt-8">
        {events.length === 0 ? (
          <div className="grimoire-border rounded-lg p-8 text-center text-muted-foreground">
            No events yet.
          </div>
        ) : (
          <ol className="grimoire-border divide-y divide-border rounded-lg">
            {events.map((e) => (
              <li key={e.seq} className="grid grid-cols-[auto_auto_1fr] gap-4 p-4 text-sm">
                <span className="font-mono text-xs text-muted-foreground">
                  #{e.seq}
                </span>
                <span className="font-mono text-xs text-muted-foreground">
                  {e.ts}
                </span>
                <span>
                  <span className="font-medium text-foreground">{e.action}</span>
                  {e.agent && (
                    <span className="ml-2 font-mono text-xs text-muted-foreground">
                      by {e.agent}
                    </span>
                  )}
                  {e.payload && (
                    <span className="ml-2 font-mono text-xs text-muted-foreground">
                      {Object.entries(e.payload)
                        .filter(([k]) => !k.startsWith("_"))
                        .slice(0, 3)
                        .map(([k, v]) => `${k}=${String(v).slice(0, 24)}`)
                        .join(" ")}
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ol>
        )}
      </section>
    </main>
  );
}
