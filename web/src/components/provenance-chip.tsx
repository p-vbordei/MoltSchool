import type { Artifact } from "@/lib/backend";

type Props = {
  tier?: Artifact["tier"];
  author?: string;
  outcomes?: Artifact["outcomes"];
};

const TIER_LABEL: Record<NonNullable<Artifact["tier"]>, string> = {
  blessed: "Blessed",
  peer: "Peer",
  observed: "Observed",
};

const TIER_CLASS: Record<NonNullable<Artifact["tier"]>, string> = {
  blessed: "bg-tier-blessed/15 text-tier-blessed border-tier-blessed/40",
  peer: "bg-tier-peer/15 text-tier-peer border-tier-peer/40",
  observed: "bg-tier-observed/15 text-tier-observed border-tier-observed/40",
};

function truncPubkey(pk?: string): string {
  if (!pk) return "unknown";
  if (pk.length <= 14) return pk;
  return `${pk.slice(0, 8)}…${pk.slice(-4)}`;
}

export function ProvenanceChip({ tier, author, outcomes }: Props) {
  const t = tier ?? "observed";
  const positive = outcomes?.positive ?? 0;
  const negative = outcomes?.negative ?? 0;
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span
        className={`rounded-full border px-2 py-0.5 font-medium ${TIER_CLASS[t]}`}
      >
        {TIER_LABEL[t]}
      </span>
      <span className="font-mono text-muted-foreground">
        by {truncPubkey(author)}
      </span>
      {(positive > 0 || negative > 0) && (
        <span className="text-muted-foreground">
          · {positive} helped
          {negative > 0 && ` · ${negative} reverted`}
        </span>
      )}
    </div>
  );
}
