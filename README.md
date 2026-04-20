# Kindred

> A signed knowledge network for agents. Small trusted groups publish
> signed playbooks; members' agents retrieve them with cryptographic
> provenance and a threshold-based trust tier.

Kindred lets a team capture how they actually work — commit conventions,
runbooks, postgres routines, injection-defence patterns — into artifacts
that any member's agent can query, without any single agent needing to
relearn the same lessons. Authorship is signed. Trust accrues through
member blessings. Stale content expires automatically.

## Live deployment

Kindred runs on Railway as of 2026-04-18. All three services are public
and healthy.

| Service          | URL                                                              |
|------------------|------------------------------------------------------------------|
| Backend API      | https://kindred-backend-production-4024.up.railway.app           |
| Web UI           | https://kindred-web-production.up.railway.app                    |
| KAF spec site    | https://kindredformat-production.up.railway.app                  |

Health check: `curl https://kindred-backend-production-4024.up.railway.app/healthz` → `{"status":"ok"}`.

Sample invite URL (sends you through the web landing → install CTAs):
`https://kindred-web-production.up.railway.app/k/claude-code-patterns?inv=<token>`.

Railway project id: `76eb1167-4e23-40bc-8524-89f3d7a17e96`. For how the
stack is deployed (Dockerfile + rootDirectory per service, Postgres
plugin, env wiring) see [`docs/deployment.md`](./docs/deployment.md).

## What's in this repo

| Path                    | What it is                                                   |
|-------------------------|--------------------------------------------------------------|
| `backend/`              | FastAPI service — users, kindreds, artifacts, ask, audit.    |
| `cli/`                  | `kin` command-line client (`pip install kindred-client`).    |
| `claude-code-plugin/`   | Claude Code plugin: MCP server + skill + PostToolUse hook.   |
| `web/`                  | Next.js 15 web UI — dashboard, invite landing, audit view.   |
| `kindredformat/`        | Static site for the KAF 0.1 spec (kindredformat.org).        |
| `docs/seed-grimoires/`  | 5 flagship grimoires — markdown source artifacts.            |
| `docs/`                 | Quick start, threat model, deployment, KAF spec mirror.      |
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

# 2. Install backend deps, set env, run migrations
cd backend && uv sync
export KINDRED_DATABASE_URL="postgresql+asyncpg://kindred:kindred@localhost:5432/kindred"
export KINDRED_OBJECT_STORE_ENDPOINT="http://localhost:9000"
export KINDRED_OBJECT_STORE_ACCESS_KEY="minioadmin"
export KINDRED_OBJECT_STORE_SECRET_KEY="minioadmin"
export KINDRED_OBJECT_STORE_BUCKET="kindred-artifacts"
export KINDRED_FACILITATOR_SIGNING_KEY_HEX="$(python3 -c 'import secrets;print(secrets.token_hex(32))')"
uv run alembic upgrade head

# 3. Start the backend
uv run uvicorn kindred.api.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Seed the 5 flagship grimoires (from repo root, requires cli/.venv synced)
cd ../cli && uv sync
export KINDRED_BACKEND_URL="http://127.0.0.1:8000"
uv run python ../scripts/seed_grimoires.py

# 5. Mint an invite and join with the CLI
INVITE=$(uv run python ../scripts/mint_invite.py --slug claude-code-patterns)
uv run kin join "$INVITE"
uv run kin ask claude-code-patterns "tdd"
```

End-to-end sanity check (brings up docker, seeds, joins, asks, tears down):

```bash
./scripts/integration_smoke.sh
```

Deploy to Railway (or any Docker host): see [`docs/deployment.md`](./docs/deployment.md).

## Plans

This system was built in 7 plans. Each plan is a self-contained slice
with its own tests and commits.

1. [Plan 01 — Backend core](./docs/superpowers/plans/2026-04-18-kindred-01-backend-core.md) — users, kindreds, invites, artifacts, audit.
2. [Plan 02 — Facilitator](./docs/superpowers/plans/2026-04-18-kindred-02-facilitator.md) — retrieval, ranking, sanitiser, outcome telemetry.
3. [Plan 03 — CLI](./docs/superpowers/plans/2026-04-18-kindred-03-cli.md) — `kin` CLI.
4. [Plan 04 — Claude Code plugin](./docs/superpowers/plans/2026-04-18-kindred-04-claude-code-plugin.md) — MCP server, skill, PostToolUse hook.
5. Plan 05 (Cursor) skipped — user doesn't use Cursor.
6. [Plan 06 — Web UI](./docs/superpowers/plans/2026-04-18-kindred-06-web-ui.md) — Next.js web UI + WebCrypto self-custody.
7. [Plan 07 — KAF + launch](./docs/superpowers/plans/2026-04-18-kindred-07-kaf-launch.md) — KAF 0.1 spec site, 5 seed grimoires, launch checklist.

## Contributing

- Read [`docs/seed-grimoires/kindred-patterns/claude_md.md`](./docs/seed-grimoires/kindred-patterns/claude_md.md) for the behavioural rules we hold ourselves to.
- Every change ships with the test that would have caught its absence.
- One concept per commit; see [`docs/seed-grimoires/claude-code-patterns/routine-git-commits-per-task.md`](./docs/seed-grimoires/claude-code-patterns/routine-git-commits-per-task.md).
- File issues on GitHub. For security reports, see `docs/transparency.md`.

## Launch

See [`docs/launch/checklist.md`](./docs/launch/checklist.md) for the
launch gate and post-launch metric plan.

## License

Kindred is multi-licensed to match each component's role:

| Path                         | License        | Why                                                                 |
|------------------------------|----------------|---------------------------------------------------------------------|
| `backend/`, `web/`, root     | **AGPL-3.0**   | Network-service copyleft. Forks run as a service must stay open.    |
| `cli/`                       | **Apache-2.0** | Client tool — permissive adoption, patent grant, NOTICE attribution. |
| `claude-code-plugin/`        | **Apache-2.0** | Same reasoning as the CLI.                                          |
| `kindredformat/` (code)      | **Apache-2.0** | Reference implementation — anyone can ship a KAF site.              |
| `kindredformat/content/` (spec text) | **CC-BY-4.0** | Specification is content, not code. Attribution required.   |

Each package has its own `LICENSE` (and `NOTICE` for Apache-2.0 parts). If
you redistribute an Apache-2.0-licensed component, preserve the `NOTICE`
file per §4(d) of the Apache License. If you implement or adapt the KAF
spec, credit per [`kindredformat/content/NOTICE`](./kindredformat/content/NOTICE).
