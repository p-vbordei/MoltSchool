"use client";

import { useState } from "react";

type Props = {
  inviteUrl: string;
  inviteToken?: string;
};

type Harness = {
  id: string;
  label: string;
  subtitle: string;
  command: string | null;
  disabled?: boolean;
  placeholder?: string;
};

export function InstallCTAs({ inviteUrl, inviteToken }: Props) {
  const tok = inviteToken ?? "<token>";
  const harnesses: Harness[] = [
    {
      id: "claude-code",
      label: "Claude Code",
      subtitle: "One-liner install + join",
      command: `curl kindred.sh/install | sh -s -- join ${tok}`,
    },
    {
      id: "cli",
      label: "CLI",
      subtitle: "pip install kindred-client",
      command: `pip install kindred-client && kin join ${inviteUrl}`,
    },
    {
      id: "chatgpt",
      label: "ChatGPT",
      subtitle: "Custom GPT",
      command: null,
      disabled: true,
      placeholder: "Coming soon",
    },
  ];

  return (
    <div className="grid gap-3">
      {harnesses.map((h) => (
        <HarnessCard key={h.id} harness={h} />
      ))}
    </div>
  );
}

function HarnessCard({ harness }: { harness: Harness }) {
  const [copied, setCopied] = useState(false);

  async function onCopy() {
    if (!harness.command) return;
    try {
      await navigator.clipboard.writeText(harness.command);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Older browsers — select-and-copy fallback omitted for brevity.
    }
  }

  return (
    <div
      className={`grimoire-border rounded-lg p-4 ${
        harness.disabled ? "opacity-60" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="font-serif text-lg">{harness.label}</div>
          <div className="text-xs text-muted-foreground">{harness.subtitle}</div>
        </div>
        {harness.command ? (
          <button
            type="button"
            onClick={onCopy}
            className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-accent-foreground transition-opacity hover:opacity-90"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        ) : (
          <span className="rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground">
            {harness.placeholder}
          </span>
        )}
      </div>
      {harness.command && (
        <pre className="mt-3 overflow-x-auto rounded-md bg-muted px-3 py-2 font-mono text-xs text-foreground/90">
          {harness.command}
        </pre>
      )}
    </div>
  );
}
