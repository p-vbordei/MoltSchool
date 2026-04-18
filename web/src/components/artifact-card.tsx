import type { Artifact } from "@/lib/backend";
import { safeMarkdown } from "@/lib/sanitize";
import { ProvenanceChip } from "@/components/provenance-chip";
import { BlessButton } from "@/components/bless-button";

type Props = {
  artifact: Artifact;
  kindredSlug: string;
  /** Stable user id used to scope the IDB agent keypair lookup in BlessButton. */
  userId?: string;
};

const TYPE_ICON: Record<string, string> = {
  "moltflow/fact": "◈",
  "moltflow/procedure": "⚙",
  "moltflow/preference": "◆",
  "moltflow/decision": "▣",
};

export function ArtifactCard(props: Props) {
  const { artifact } = props;
  const icon = TYPE_ICON[artifact.type] ?? "◇";
  const html = artifact.content ? safeMarkdown(artifact.content) : "";
  return (
    <article className="grimoire-border rounded-lg p-5">
      <header className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span
              className="font-mono text-lg text-accent"
              aria-hidden="true"
              title={artifact.type}
            >
              {icon}
            </span>
            <h3 className="font-serif text-lg">{artifact.logical_name}</h3>
          </div>
          <div className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            {artifact.type}
            {artifact.valid_until && ` · valid until ${artifact.valid_until}`}
          </div>
        </div>
      </header>

      {html && (
        <div
          className="prose-grimoire mt-4 text-sm"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: html }}
        />
      )}

      {artifact.tags && artifact.tags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {artifact.tags.map((t) => (
            <span
              key={t}
              className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
            >
              #{t}
            </span>
          ))}
        </div>
      )}

      <footer className="mt-4 flex items-center justify-between gap-4 border-t border-border pt-3">
        <ProvenanceChip
          tier={artifact.tier}
          author={artifact.author_pubkey}
          outcomes={artifact.outcomes}
        />
        <div className="flex items-center gap-3">
          <BlessButton
            kindredSlug={props.kindredSlug}
            contentId={artifact.content_id}
            alreadyBlessed={false}
            userId={props.userId}
          />
          <div className="font-mono text-[10px] text-muted-foreground">
            cid {artifact.content_id.slice(0, 12)}…
          </div>
        </div>
      </footer>
    </article>
  );
}
