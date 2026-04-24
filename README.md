# Kindred

> A shared notebook for your team. You write. Every teammate's AI reads.

## The problem

Two engineers. Same team. Same sprint. Both ask their Claude, "add a
migration for a `users.role` column."

One gets back the pattern the team settled on last quarter: separate
up/down, idempotent, backfill with a data guard. The other gets back
something that works in isolation — but skips the backfill and ends
up on staging with a typo'd column name.

Code review catches the drift. Someone reruns the migration. An hour
goes sideways.

The model isn't the problem. Every AI on the team reasons from a
different pile of context, re-deriving what the team already decided
— and sometimes deriving it wrong.

## What Kindred does

You write the routine once. Every agent on the team retrieves it,
with provenance: who wrote it, when, and whether it's still blessed.
Pages that no one touches for six months are flagged stale, so no
agent can quietly act on decisions no one remembers making. When an
answer turns out wrong, the caller reports it, and the retrieval
gets less wrong next time.

Kindred doesn't generate. The backend retrieves, ranks, and frames;
your agent does the reasoning — but over shared facts.

## Install

```bash
pip install kindred-client
kin install claude-code-patterns
kin ask claude-code-patterns "how do we structure commits?"
```

Three commands. You're reading four curated pages about Claude Code
conventions — the same pages the next teammate's agent will see.
Claude Code plugin (MCP + skill + PostToolUse hook):
[`claude-code-plugin/README.md`](./claude-code-plugin/README.md).

## Live deployment

Kindred runs on Railway.

| Service     | URL                                                      |
|-------------|----------------------------------------------------------|
| Backend API | https://kindred-backend-production-4024.up.railway.app   |
| Web UI      | https://kindred-web-production.up.railway.app            |
| KAF spec    | https://kindredformat-production.up.railway.app          |

Health: `curl .../healthz` → `{"status":"ok"}`.

## Repo layout

| Path                    | What it is                                               |
|-------------------------|----------------------------------------------------------|
| `backend/`              | FastAPI — users, kindreds, artifacts, ask, audit.        |
| `cli/`                  | `kin` CLI (`pip install kindred-client`).                |
| `claude-code-plugin/`   | Claude Code plugin: MCP + skill + PostToolUse hook.      |
| `web/`                  | Next.js 15 — dashboard, invite landing, audit view.      |
| `kindredformat/`        | KAF 0.1 spec site.                                       |
| `docs/seed-grimoires/`  | Five starter notebooks you can seed.                     |
| `scripts/`              | Seed, invite mint, onboarding benchmark, smoke test.     |

## Network health

Every kindred surfaces four indicators at `/dashboard/<slug>/health`:

- **Retrieval utility** — success rate, top-1 precision, mean rank.
- **Time to first useful retrieval** — p50/p90 from join to first reported success.
- **Trust propagation** — p50/p90 from publish to threshold-th blessing.
- **Staleness cost** — shadow hits plus soon-to-expire returns over 7 days.

JSON: `GET /v1/kindreds/<slug>/health` with a member's `X-Agent-Pubkey`.

## Run locally

```bash
./scripts/integration_smoke.sh
```

Brings up Postgres, runs migrations, starts the backend, seeds all
five grimoires, joins with a test agent, asks a question, tears
down. Step-by-step: [`docs/quick-start.md`](./docs/quick-start.md).
Railway deploy: [`docs/deployment.md`](./docs/deployment.md).

## KAF spec

The Kindred Artifact Format 0.1 — how pages are stored and signed.

- [Spec](./kindredformat/content/kaf-spec-0.1.md)
- [Examples](./kindredformat/content/kaf-examples.md)
- [Implementers guide](./kindredformat/content/kaf-implementers-guide.md)

## License

Multi-licensed by role. Each package has its own `LICENSE` (and
`NOTICE` for Apache-2.0 parts); redistribution must preserve
`NOTICE` per §4(d).

| Path                                             | License    |
|--------------------------------------------------|------------|
| `backend/`, `web/`, root                         | AGPL-3.0   |
| `cli/`, `claude-code-plugin/`, `kindredformat/` (code) | Apache-2.0 |
| `kindredformat/content/` (spec text)             | CC-BY-4.0  |

## Contributing

- Behavioural rules: [`kindred-patterns/claude_md.md`](./docs/seed-grimoires/kindred-patterns/claude_md.md).
- Every change ships with the test that would have caught its absence.
- One concept per commit.
- Security reports: [`docs/transparency.md`](./docs/transparency.md).

Launch gate: [`docs/launch/checklist.md`](./docs/launch/checklist.md).
