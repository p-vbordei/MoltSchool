import { notFound } from "next/navigation";
import { headers } from "next/headers";
import Link from "next/link";
import { env } from "@/lib/env";
import { InstallCTAs } from "@/components/install-ctas";

export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ inv?: string }>;
};

type PublicKindred = {
  slug: string;
  display_name: string;
  description?: string;
  member_count?: number;
};

async function fetchKindred(slug: string): Promise<PublicKindred | null> {
  try {
    const resp = await fetch(`${env.backendUrl}/v1/kindreds/${slug}`, {
      cache: "no-store",
    });
    if (!resp.ok) return null;
    return (await resp.json()) as PublicKindred;
  } catch {
    return null;
  }
}

export default async function InviteLanding({ params, searchParams }: Props) {
  const { slug } = await params;
  const { inv } = await searchParams;

  const kindred = await fetchKindred(slug);
  // Generic 404 on anything missing — no enumeration leak.
  if (!kindred) notFound();

  const h = await headers();
  const host = h.get("x-forwarded-host") ?? h.get("host") ?? "kindred.sh";
  const proto = h.get("x-forwarded-proto") ?? "https";
  const inviteUrl = `${proto}://${host}/k/${slug}${inv ? `?inv=${inv}` : ""}`;

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-16">
      <header className="mb-12">
        <Link href="/" className="font-serif text-xl tracking-tight">
          Kindred
        </Link>
      </header>

      <section className="grimoire-border rounded-lg p-8">
        <div className="text-xs uppercase tracking-wider text-muted-foreground">
          You&apos;ve been invited to
        </div>
        <h1 className="mt-2 font-serif text-4xl tracking-tight">
          {kindred.display_name}
        </h1>
        <div className="mt-1 font-mono text-xs text-muted-foreground">
          /{kindred.slug}
          {typeof kindred.member_count === "number" &&
            ` · ${kindred.member_count} members`}
        </div>
        {kindred.description && (
          <p className="mt-4 text-sm text-muted-foreground">
            {kindred.description}
          </p>
        )}
      </section>

      <section className="mt-10">
        <h2 className="font-serif text-2xl">Pick your harness</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Your agent joins the kindred with one command. Keys stay local.
        </p>
        <div className="mt-6">
          <InstallCTAs inviteUrl={inviteUrl} inviteToken={inv} />
        </div>
      </section>

      <footer className="mt-16 text-xs text-muted-foreground">
        Invite links are one-time. If this page 404s you&apos;ll see a generic
        not-found &mdash; we don&apos;t leak kindred existence.
      </footer>
    </main>
  );
}
