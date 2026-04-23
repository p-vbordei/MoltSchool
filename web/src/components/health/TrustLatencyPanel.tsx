import { IndicatorCard } from "./IndicatorCard";
import type { KindredHealth } from "@/lib/backend";

function fmt(sec: number | null): string {
  if (sec === null) return "—";
  if (sec < 3600) return `${Math.round(sec / 60)}m`;
  if (sec < 86400) return `${(sec / 3600).toFixed(1)}h`;
  return `${(sec / 86400).toFixed(1)}d`;
}

export function TrustLatencyPanel({
  tp,
}: {
  tp: KindredHealth["trust_propagation"];
}) {
  return (
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <IndicatorCard
        label="Promoted artifacts"
        value={String(tp.promoted_artifacts)}
        hint="Reached bless threshold"
      />
      <IndicatorCard
        label="Propagation p50"
        value={fmt(tp.p50_seconds)}
        hint="publish → threshold-blessing"
      />
      <IndicatorCard label="Propagation p90" value={fmt(tp.p90_seconds)} />
    </section>
  );
}
