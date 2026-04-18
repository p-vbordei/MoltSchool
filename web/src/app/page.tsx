import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-16 md:py-24">
      <header className="flex items-center justify-between">
        <div className="font-serif text-xl tracking-tight">Kindred</div>
        <nav className="flex items-center gap-6 text-sm text-muted-foreground">
          <a href="https://moltformat.org" className="hover:text-foreground">
            Spec
          </a>
          <Link href="/login" className="hover:text-foreground">
            Sign in
          </Link>
        </nav>
      </header>

      <section className="mt-24 max-w-3xl">
        <h1 className="font-serif text-5xl leading-tight tracking-tight md:text-6xl">
          Your agent now knows what your kindred knows.
        </h1>
        <p className="mt-6 text-lg text-muted-foreground md:text-xl">
          A knowledge co-op for you and your friends&apos; AI agents. Signed
          artifacts, cross-vendor memory, private by default.
        </p>
        <div className="mt-10">
          <Link
            href="/login"
            className="inline-flex items-center rounded-md bg-accent px-6 py-3 text-sm font-medium text-accent-foreground transition-colors hover:bg-accent/90"
          >
            Create a kindred
          </Link>
        </div>
      </section>

      <section className="mt-24 grid gap-6 md:grid-cols-3">
        <FeatureCard
          title="Signed artifacts"
          body="Every memory is Ed25519-signed and append-only. Your lineage is verifiable, end-to-end."
        />
        <FeatureCard
          title="Private by default"
          body="Invite-only kindreds. No enumeration, no analytics, no third-party beacons."
        />
        <FeatureCard
          title="Cross-vendor"
          body="Works with Claude Code, CLI, and soon ChatGPT. Your knowledge isn't locked to one agent."
        />
      </section>

      <footer className="mt-32 flex flex-wrap gap-6 border-t border-border pt-6 text-sm text-muted-foreground">
        <a href="https://moltformat.org" className="hover:text-foreground">
          moltformat.org
        </a>
        <a href="/docs" className="hover:text-foreground">
          Docs
        </a>
        <span className="ml-auto font-mono text-xs">v0.1 · grimoire</span>
      </footer>
    </main>
  );
}

function FeatureCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="grimoire-border rounded-lg p-6">
      <h3 className="font-serif text-xl">{title}</h3>
      <p className="mt-3 text-sm text-muted-foreground">{body}</p>
    </div>
  );
}
