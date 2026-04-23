import { IndicatorCard } from "./IndicatorCard";
import type { KindredHealth } from "@/lib/backend";

export function StalenessPanel({
  sc,
}: {
  sc: KindredHealth["staleness_cost"];
}) {
  return (
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <IndicatorCard
        label="Shadow hits (7d)"
        value={String(sc.shadow_hits_last_7d)}
        hint="Expired artefacts that would have ranked top-K"
        tone={sc.shadow_hits_last_7d === 0 ? "good" : "warn"}
      />
      <IndicatorCard
        label="Expiring soon (7d)"
        value={String(sc.expiring_soon_hits_last_7d)}
        hint="Asks where returned artifact expires within 7d"
      />
    </section>
  );
}
