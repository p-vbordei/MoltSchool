import { IndicatorCard } from "./IndicatorCard";
import type { KindredHealth } from "@/lib/backend";

export function RetrievalUtilityPanel({
  ru,
}: {
  ru: KindredHealth["retrieval_utility"];
}) {
  const successPct = (ru.success_rate * 100).toFixed(0);
  const top1Pct = (ru.top1_precision * 100).toFixed(0);
  return (
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-4">
      <IndicatorCard
        label="Total asks"
        value={String(ru.total_asks)}
        hint="All time"
      />
      <IndicatorCard
        label="Outcomes reported"
        value={`${ru.total_outcomes} (${ru.total_asks ? Math.round((ru.total_outcomes / ru.total_asks) * 100) : 0}%)`}
        hint="Reporting coverage"
      />
      <IndicatorCard
        label="Success rate"
        value={`${successPct}%`}
        tone={ru.success_rate >= 0.7 ? "good" : "warn"}
        hint="success + partial"
      />
      <IndicatorCard
        label="Top-1 precision"
        value={`${top1Pct}%`}
        hint={`Mean rank of chosen: ${ru.mean_rank_of_chosen.toFixed(1)}`}
        tone={ru.top1_precision >= 0.5 ? "good" : "warn"}
      />
    </section>
  );
}
