import type { Artifact } from "@/lib/backend";

type Props = {
  blessingsCount?: Artifact["blessings_count"];
  blessThreshold?: Artifact["bless_threshold"];
  validUntil?: Artifact["valid_until"];
  /** Inject for deterministic snapshots in tests. */
  now?: Date;
};

const DAY_MS = 24 * 60 * 60 * 1000;

type ExpiryState =
  | { kind: "none" }
  | { kind: "expired"; days: number }
  | { kind: "critical"; days: number }
  | { kind: "warn"; days: number }
  | { kind: "ok"; days: number };

function expiryState(validUntil?: string, now: Date = new Date()): ExpiryState {
  if (!validUntil) return { kind: "none" };
  const until = Date.parse(validUntil);
  if (Number.isNaN(until)) return { kind: "none" };
  const days = Math.floor((until - now.getTime()) / DAY_MS);
  if (days < 0) return { kind: "expired", days: Math.abs(days) };
  if (days < 7) return { kind: "critical", days };
  if (days < 30) return { kind: "warn", days };
  return { kind: "ok", days };
}

const EXPIRY_CLASS: Record<Exclude<ExpiryState["kind"], "none">, string> = {
  expired: "bg-red-500/15 text-red-600 border-red-500/40",
  critical: "bg-orange-500/15 text-orange-600 border-orange-500/40",
  warn: "bg-yellow-500/15 text-yellow-700 border-yellow-500/40",
  ok: "bg-emerald-500/10 text-emerald-700 border-emerald-500/30",
};

function expiryLabel(s: Exclude<ExpiryState, { kind: "none" }>): string {
  switch (s.kind) {
    case "expired":
      return s.days === 0 ? "expired today" : `expired ${s.days}d ago`;
    case "critical":
    case "warn":
    case "ok":
      return s.days === 0
        ? "expires today"
        : `expires in ${s.days}d`;
  }
}

export function TrustBadges({
  blessingsCount,
  blessThreshold,
  validUntil,
  now,
}: Props) {
  const showBless =
    typeof blessingsCount === "number" && typeof blessThreshold === "number";
  const reached = showBless && blessingsCount! >= blessThreshold!;
  const exp = expiryState(validUntil, now);

  return (
    <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
      {showBless && (
        <span
          title={`${blessingsCount} of ${blessThreshold} required blessings`}
          aria-label={`blessings ${blessingsCount} of ${blessThreshold}`}
          className={
            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono " +
            (reached
              ? "border-tier-blessed/40 bg-tier-blessed/15 text-tier-blessed"
              : "border-muted-foreground/30 bg-muted text-muted-foreground")
          }
        >
          <span aria-hidden="true">◈</span>
          {blessingsCount}/{blessThreshold}
        </span>
      )}
      {exp.kind !== "none" && (
        <span
          title={`valid until ${validUntil}`}
          aria-label={expiryLabel(exp)}
          className={
            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 " +
            EXPIRY_CLASS[exp.kind]
          }
        >
          <span aria-hidden="true">⏳</span>
          {expiryLabel(exp)}
        </span>
      )}
    </div>
  );
}
