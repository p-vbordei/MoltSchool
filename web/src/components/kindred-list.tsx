import Link from "next/link";
import type { Kindred } from "@/lib/backend";

type Props = {
  kindreds: Kindred[];
};

export function KindredList({ kindreds }: Props) {
  if (!kindreds.length) {
    return (
      <div className="grimoire-border rounded-lg p-8 text-center">
        <p className="text-muted-foreground">
          No kindreds yet. Create one, or accept an invite to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {kindreds.map((k) => (
        <Link
          key={k.slug}
          href={`/dashboard/${k.slug}`}
          className="grimoire-border block rounded-lg p-5 transition-colors hover:border-accent"
        >
          <div className="font-serif text-xl">{k.display_name}</div>
          <div className="mt-1 font-mono text-xs text-muted-foreground">
            /{k.slug}
          </div>
          {k.description && (
            <p className="mt-3 line-clamp-2 text-sm text-muted-foreground">
              {k.description}
            </p>
          )}
          <div className="mt-4 flex gap-4 text-xs text-muted-foreground">
            {typeof k.member_count === "number" && (
              <span>{k.member_count} members</span>
            )}
            {typeof k.artifact_count === "number" && (
              <span>{k.artifact_count} artifacts</span>
            )}
          </div>
        </Link>
      ))}
    </div>
  );
}
