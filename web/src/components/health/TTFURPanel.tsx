import { IndicatorCard } from "./IndicatorCard";
import type { KindredHealth } from "@/lib/backend";

function fmt(sec: number | null): string {
  if (sec === null) return "—";
  if (sec < 90) return `${Math.round(sec)}s`;
  if (sec < 3600) return `${Math.round(sec / 60)}m`;
  return `${(sec / 3600).toFixed(1)}h`;
}

export function TTFURPanel({ ttfur }: { ttfur: KindredHealth["ttfur"] }) {
  return (
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <IndicatorCard
        label="Sample size"
        value={String(ttfur.sample_size)}
        hint="Agents with at least one success"
      />
      <IndicatorCard
        label="TTFUR p50"
        value={fmt(ttfur.p50_seconds)}
        tone={
          ttfur.p50_seconds !== null && ttfur.p50_seconds < 60
            ? "good"
            : "warn"
        }
      />
      <IndicatorCard label="TTFUR p90" value={fmt(ttfur.p90_seconds)} />
    </section>
  );
}
