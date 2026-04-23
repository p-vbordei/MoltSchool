import { redirect } from "next/navigation";
import Link from "next/link";
import { auth } from "@/lib/auth";
import { backend, type KindredHealth } from "@/lib/backend";
import { RetrievalUtilityPanel } from "@/components/health/RetrievalUtilityPanel";
import { TTFURPanel } from "@/components/health/TTFURPanel";
import { TrustLatencyPanel } from "@/components/health/TrustLatencyPanel";
import { StalenessPanel } from "@/components/health/StalenessPanel";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ slug: string }> };

export default async function HealthPage({ params }: Props) {
  const session = await auth();
  if (!session) redirect("/login");
  const { slug } = await params;

  let health: KindredHealth | null = null;
  try {
    health = await backend.health.get(slug);
  } catch (err) {
    console.error("[health] fetch failed", err);
  }

  if (!health) {
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
        <div className="grimoire-border rounded-lg p-8 text-center text-muted-foreground">
          Could not load health data.
        </div>
      </main>
    );
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
        <h1 className="font-serif text-3xl tracking-tight">Network health</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Indicators generated {new Date(health.generated_at).toLocaleString()}.
        </p>
      </header>

      <section className="mt-8 space-y-10">
        <div>
          <h2 className="font-serif text-lg">Retrieval utility</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            How often the network surfaces what agents actually use.
          </p>
          <div className="mt-4">
            <RetrievalUtilityPanel ru={health.retrieval_utility} />
          </div>
        </div>

        <div>
          <h2 className="font-serif text-lg">
            Time to first useful retrieval
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            How quickly a new agent finds something that works.
          </p>
          <div className="mt-4">
            <TTFURPanel ttfur={health.ttfur} />
          </div>
        </div>

        <div>
          <h2 className="font-serif text-lg">Trust propagation</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            How fast an artifact reaches the bless threshold after publish.
          </p>
          <div className="mt-4">
            <TrustLatencyPanel tp={health.trust_propagation} />
          </div>
        </div>

        <div>
          <h2 className="font-serif text-lg">Staleness cost</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Retrievals hurt by expired or soon-to-expire artifacts.
          </p>
          <div className="mt-4">
            <StalenessPanel sc={health.staleness_cost} />
          </div>
        </div>
      </section>
    </main>
  );
}
