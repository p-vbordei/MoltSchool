import { redirect, notFound } from "next/navigation";
import Link from "next/link";
import { auth } from "@/lib/auth";
import { backend, BackendError, type Artifact } from "@/lib/backend";
import { ArtifactCard } from "@/components/artifact-card";

export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{ slug: string }>;
};

export default async function KindredView({ params }: Props) {
  const session = await auth();
  if (!session) redirect("/login");

  const { slug } = await params;

  let kindred: Awaited<ReturnType<typeof backend.kindreds.get>> | null = null;
  let artifacts: Artifact[] = [];
  try {
    kindred = await backend.kindreds.get(slug);
  } catch (err) {
    if (err instanceof BackendError && err.status === 404) notFound();
    throw err;
  }
  try {
    const resp = await backend.artifacts.list(slug);
    artifacts = resp.artifacts ?? [];
  } catch (err) {
    console.error("[kindred] list artifacts failed", err);
  }

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-6 py-12">
      <nav className="mb-8 text-sm">
        <Link href="/dashboard" className="text-muted-foreground hover:text-foreground">
          ← All kindreds
        </Link>
      </nav>

      <header className="border-b border-border pb-6">
        <h1 className="font-serif text-4xl tracking-tight">
          {kindred.display_name}
        </h1>
        <div className="mt-1 font-mono text-xs text-muted-foreground">
          /{kindred.slug}
        </div>
        {kindred.description && (
          <p className="mt-3 text-sm text-muted-foreground">
            {kindred.description}
          </p>
        )}
      </header>

      <nav className="mt-6 flex gap-1 border-b border-border text-sm">
        <TabLink href={`/dashboard/${slug}`} label="Artifacts" active />
        <TabLink href={`/dashboard/${slug}/audit`} label="Audit" />
        <TabLink href={`/dashboard/${slug}/rollback`} label="Rollback" />
      </nav>

      <section className="mt-8 grid gap-4 md:grid-cols-2">
        {artifacts.length === 0 ? (
          <div className="grimoire-border col-span-full rounded-lg p-8 text-center text-muted-foreground">
            No artifacts yet. Use <code className="font-mono">kin contribute</code>{" "}
            from the CLI, or ask an agent to propose one.
          </div>
        ) : (
          artifacts.map((a) => (
            <ArtifactCard
              key={a.content_id}
              artifact={a}
              kindredSlug={slug}
            />
          ))
        )}
      </section>
    </main>
  );
}

function TabLink({
  href,
  label,
  active,
}: {
  href: string;
  label: string;
  active?: boolean;
}) {
  return (
    <Link
      href={href}
      className={`px-4 py-2 transition-colors ${
        active
          ? "border-b-2 border-accent text-foreground"
          : "text-muted-foreground hover:text-foreground"
      }`}
    >
      {label}
    </Link>
  );
}
