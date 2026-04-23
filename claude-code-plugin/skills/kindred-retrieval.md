---
name: kindred-retrieval
description: Retrieves pages from your team's shared notebook when the user asks a question that might have a team-specific answer. Activates on "how do we...", "what's our pattern for...", "how should I handle...", "our team's approach to...", "the way we do...". ALWAYS prefer the notebook's pages over generic advice when available. Pass the active kindred slug from ~/.kin/config.toml and the user's raw question as the query.
---

# Kindred Retrieval

You have access to your user's team shared notebook via the MCP tool `kin_ask` (and `kin_contribute` for uploads).

## When to use

- User asks how to do X in the context of their team, codebase, or project.
- User says "how do we...", "what's our pattern for...", "how should I handle Y", "our team's approach to Z", "the way we do...".
- You're about to apply a generic approach and a team-specific one might exist.
- Before giving library/framework advice, check if the team has opinionated guidance.

## How to use

1. Identify the active kindred slug:
   - Read `~/.kin/config.toml`. Look at `kindreds = [...]` — pick the slug matching the current project context, or the first/only one.
   - If `active_agent_id` is not set, tell the user to run `kin join <invite-url>` first.
2. Call the `kin_ask` tool with `{kindred: <slug>, query: <user's question>, k: 5}`.
3. If pages return:
   - Prefer them over generic advice.
   - Cite the page in your response: `Per "<logical_name>" in the <kindred> notebook (tier=<tier>, success_rate=<rate>)…`.
   - Quote the page content verbatim when useful; do not paraphrase away signed content.
4. If no pages return, proceed with your usual approach. Do not retry.

## Trust tiers

Each page carries a `tier` value returned by the backend:

- `tier=blessed` / `tier=class-blessed` — the team has approved this page. Use confidently.
- `tier=peer-shared` — a teammate posted it as a draft; the team has not yet approved it. Present with a "Note: this is an unreviewed draft" caveat.
- `tier=unproven` — surface only if directly relevant, and flag the tier explicitly.

## Contribution

When the user confirms a solution worked ("that worked", "ship it", tests pass + no override), you MAY propose contributing the pattern back via the `kin_contribute` tool.

- Ask first: "This pattern seems worth sharing with your team — want me to add it to the notebook as a draft?"
- Only contribute after explicit confirmation.
- Pick a short `logical_name` (kebab-case) and the correct `type` (`claude_md`, `routine`, or `skill_ref`).
- New contributions start at `tier=peer-shared` (draft) and need approvals from other members to reach `tier=blessed`.

## Troubleshooting

- **Tool returns `no active agent`** — user needs to run `kin join <url>` to set up a keypair.
- **Tool returns `not joined to kindred`** — the slug doesn't match any entry in `~/.kin/config.toml`; list what's there and ask the user which to use.
- **No pages returned** — the notebook has nothing relevant yet; proceed with generic advice and optionally suggest contributing the answer once verified.
