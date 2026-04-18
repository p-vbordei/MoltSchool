# Kindred

> A signed knowledge network for agents. Small trusted groups publish
> signed playbooks; members' agents retrieve them with cryptographic
> provenance and a threshold-based trust tier.

Kindred lets a team capture how they actually work — commit conventions,
runbooks, postgres routines, injection-defence patterns — into artifacts
that any member's agent can query, without any single agent needing to
relearn the same lessons. Authorship is signed. Trust accrues through
member blessings. Stale content expires automatically.

## What's in this repo

| Path                    | What it is                                                   |
|-------------------------|--------------------------------------------------------------|
| `backend/`              | FastAPI service — users, kindreds, artifacts, ask, audit.   |
| `cli/`                  | `kin` command-line client (`pip install kindred-client`).    |
| `claude-code-plugin/`   | Claude Code plugin: MCP server + skill + PostToolUse hook.  |
| `web/`                  | Next.js 15 web UI — dashboard, invite landing, audit view.  |
| `kindredformat/`        | Static site for the KAF 0.1 spec (kindredformat.org).        |
| `docs/seed-grimoires/`  | 5 flagship grimoires — markdown source artifacts.            |
| `docs/`                 | Quick start, threat model, transparency, KAF spec mirror.    |
| `scripts/`              | Seed, invite-mint, onboarding benchmark, integration smoke.  |
| `.github/workflows/`    | CI — backend, cli, web, and weekly launch benchmark.         |

## Quick start

```bash
pip install kindred-client
kin join <invite-url>
kin ask claude-code-patterns "how do I structure commits?"
```

Full quick start: [`docs/quick-start.md`](./docs/quick-start.md).

## KAF spec

The Kindred Artifact Format 0.1 is published as a static site; the
source markdown lives in this repo.

- Spec: [`kindredformat/content/kaf-spec-0.1.md`](./kindredformat/content/kaf-spec-0.1.md)
- Examples: [`kindredformat/content/kaf-examples.md`](./kindredformat/content/kaf-examples.md)
- Implementers guide: [`kindredformat/content/kaf-implementers-guide.md`](./kindredformat/content/kaf-implementers-guide.md)

## Run locally

```bash
# 1. Start Postgres + MinIO
docker compose -f backend/docker-compose.yml up -d

# 2. Install backend deps and run migrations
cd backend && uv sync && uv run alembic upgrade head

# 3. Start the backend
uv run uvicorn kindred.api.app:app --reload

# 4. Seed the 5 flagship grimoires
python ../scripts/seed_grimoires.py

# 5. Install the CLI and join
pip install ../cli
kin join "$(python ../scripts/mint_invite.py --slug claude-code-patterns)"
kin ask claude-code-patterns "tdd"
```

End-to-end sanity check:

```bash
./scripts/integration_smoke.sh
```

## Plans

This system was built in 7 plans. Each plan is a self-contained slice
with its own tests and commits.

1. [`docs/superpowers/plans/2026-04-18-kindred-01-backend-core.md`](./docs/superpowers/plans/2026-04-18-kindred-01-backend-core.md) — users, kindreds, invites, artifacts, audit.
2. [`2026-04-18-kindred-02-facilitator.md`](./docs/superpowers/plans/2026-04-18-kindred-02-facilitator.md) — retrieval, ranking, sanitiser, outcome telemetry.
3. [`2026-04-18-kindred-03-cli.md`](./docs/superpowers/plans/2026-04-18-kindred-03-cli.md) — `kin` CLI.
4. [`2026-04-18-kindred-04-claude-code-plugin.md`](./docs/superpowers/plans/2026-04-18-kindred-04-claude-code-plugin.md) — Claude Code plugin.
5. Plan 05 was merged into 02 during execution.
6. [`2026-04-18-kindred-06-web-ui.md`](./docs/superpowers/plans/2026-04-18-kindred-06-web-ui.md) — Next.js web UI.
7. [`2026-04-18-kindred-07-kaf-launch.md`](./docs/superpowers/plans/2026-04-18-kindred-07-kaf-launch.md) — KAF spec + launch package (this plan).

## Contributing

- Read [`docs/seed-grimoires/kindred-patterns/claude_md.md`](./docs/seed-grimoires/kindred-patterns/claude_md.md) for the behavioural rules we hold ourselves to.
- Every change ships with the test that would have caught its absence.
- One concept per commit; see [`docs/seed-grimoires/claude-code-patterns/routine-git-commits-per-task.md`](./docs/seed-grimoires/claude-code-patterns/routine-git-commits-per-task.md).
- File issues on GitHub. For security reports, see `docs/transparency.md`.

## Launch

See [`docs/launch/checklist.md`](./docs/launch/checklist.md) for the
launch gate and post-launch metric plan.

## License

MIT. See `LICENSE` in each package.
