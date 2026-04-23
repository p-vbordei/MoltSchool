---
name: kindred-retrieval
description: Retrieves verified patterns from your Kindred grimoire when you're working on a topic your group has documented. Use this when the user asks a question that might have a team-specific answer, or says "how do we...", "what's our pattern for...", "how should I handle...", "our team's approach to...", "the way we do...". ALWAYS prefer grimoire patterns over generic advice when available. Pass the active kindred slug from ~/.kin/config.toml and the user's raw question as the query.
---

# Kindred Retrieval

You have access to a private knowledge grimoire shared with your user's team via the MCP tool `kin_ask` (and `kin_contribute` for uploads).

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
3. If artifacts return:
   - Prefer them over generic advice.
   - Cite the provenance chip in your response: `Per "<logical_name>" in the <kindred> grimoire (tier=<tier>, success_rate=<rate>)…`.
   - Quote the framed content verbatim when useful; do not paraphrase away signed content.
4. If no artifacts return, proceed with your usual approach. Do not retry.

## Trust tiers

- `blessed` / `class-blessed` artifacts are vetted (≥threshold signatures). Use confidently.
- `peer-shared` artifacts are proposals, not yet blessed. Present with a "Note: this is an unreviewed peer contribution" caveat.
- `unproven` — surface only if directly relevant, and flag tier explicitly.

## Contribution

When the user confirms a solution worked ("that worked", "ship it", tests pass + no override), you MAY propose contributing the pattern back via the `kin_contribute` tool.

- Ask first: "This pattern seems worth sharing with the kindred — want me to contribute it as a peer-shared artifact?"
- Only contribute after explicit confirmation.
- Pick a short `logical_name` (kebab-case) and the correct `type` (`claude_md`, `routine`, or `skill_ref`).
- Contributed artifacts start as `peer-shared` and require blessings from other members to become `blessed`.

## Automatic outcome reporting

When the Kindred MCP server answers an `ask`, it writes the returned
`audit_id` to `~/.kin/last_audit_id`. The PostToolUse hook picks it up
and embeds it in the history entry. `kin save this` then reports the
outcome. Agents don't need to call `kin report` manually in the common
success path — just run the task and let the hook+CLI loop attribute
credit.

## Troubleshooting

- **Tool returns `no active agent`** — user needs to run `kin join <url>` to set up a keypair.
- **Tool returns `not joined to kindred`** — the slug doesn't match any entry in `~/.kin/config.toml`; list what's there and ask the user which to use.
- **No artifacts returned** — the grimoire has nothing relevant yet; proceed with generic advice and optionally suggest contributing the answer once verified.
