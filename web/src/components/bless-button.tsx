"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { hex, pubkeyToStr, sign } from "@/lib/crypto/keys";
import { loadKeypair } from "@/lib/crypto/keystore";

type Props = {
  kindredSlug: string;
  contentId: string;
  alreadyBlessed?: boolean;
  /**
   * Stable user identifier used to namespace the IndexedDB agent keypair.
   * Passed down from the RSC dashboard so the client component doesn't need
   * a SessionProvider. If undefined, the button surfaces a load error.
   */
  userId?: string;
};

export function BlessButton({
  kindredSlug,
  contentId,
  alreadyBlessed,
  userId,
}: Props) {
  const [open, setOpen] = useState(false);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function confirm() {
    setError(null);
    startTransition(async () => {
      try {
        if (!userId) throw new Error("no session — please sign in again");
        const agent = await loadKeypair(`agent-${userId}`);
        if (!agent) {
          throw new Error(
            "agent key not found — refresh the page to re-bootstrap"
          );
        }

        // Canonical payload for the bless signature: raw UTF-8 bytes of the
        // content_id string. Matches backend `add_blessing` which calls
        // `verify(signer_pubkey, content_id.encode(), sig)`.
        const message = new TextEncoder().encode(contentId);
        const sig = await sign(agent.sk, message);

        const resp = await fetch(
          `/api/backend/kindreds/${kindredSlug}/artifacts/${contentId}/bless`,
          {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({
              signer_pubkey: pubkeyToStr(agent.pk),
              sig: hex(sig),
            }),
          }
        );
        if (!resp.ok) {
          const body = (await resp.json().catch(() => ({}))) as {
            message?: string;
          };
          throw new Error(body.message ?? `bless failed (${resp.status})`);
        }
        setOpen(false);
        router.refresh();
      } catch (e) {
        setError(e instanceof Error ? e.message : "bless failed");
      }
    });
  }

  if (alreadyBlessed) {
    return (
      <span className="text-xs text-muted-foreground">✓ you blessed this</span>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-md border border-border px-3 py-1 text-xs hover:border-accent hover:text-accent"
      >
        Bless
      </button>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-6 backdrop-blur-sm"
        >
          <div className="grimoire-border w-full max-w-md rounded-lg p-6">
            <h2 className="font-serif text-xl">Bless this artifact?</h2>
            <p className="mt-3 text-sm text-muted-foreground">
              You&apos;re signing this artifact&apos;s content_id with your
              agent key. This is a public, append-only endorsement visible
              to every member of the kindred.
            </p>
            <pre className="mt-3 overflow-x-auto rounded-md bg-muted px-2 py-1 font-mono text-[10px] text-muted-foreground">
              {contentId}
            </pre>
            {error && (
              <p className="mt-3 text-xs text-red-400">{error}</p>
            )}
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground"
                disabled={pending}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirm}
                className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-accent-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
                disabled={pending}
              >
                {pending ? "Signing…" : "Bless"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
