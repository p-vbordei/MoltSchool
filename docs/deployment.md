# Deployment — Kindred on Railway

This project is deployed to [Railway](https://railway.com) as 4 services
on a single project. This doc covers (a) the architecture, (b) how to
redeploy or stand up a fresh copy, and (c) the seven failure modes we
hit on first deploy so you don't repeat them.

**Live project id:** `76eb1167-4e23-40bc-8524-89f3d7a17e96`
(`Vlad Bordei's Projects` workspace).

## Service topology

| Railway service   | Source          | Port (internal) | Public domain                                              |
|-------------------|-----------------|-----------------|------------------------------------------------------------|
| `Postgres-EBkW`   | managed plugin  | 5432            | internal only (`postgres-ebkw.railway.internal`)           |
| `kindred-backend` | `backend/`      | 8080 (auto)     | https://kindred-backend-production-4024.up.railway.app     |
| `kindred-web`     | `web/`          | 3000            | https://kindred-web-production.up.railway.app              |
| `kindredformat`   | `kindredformat/`| 3000            | https://kindredformat-production.up.railway.app            |

All three application services:
- Builder: `DOCKERFILE` (not Railpack)
- Root directory: the service's folder (e.g. `/backend`) — set via
  `serviceInstanceUpdate(rootDirectory: ...)` mutation on create
- Dockerfile path: `Dockerfile` (relative to the root directory)

The backend's `$PORT` is injected by Railway (currently 8080) and the
Dockerfile binds uvicorn to it via `${PORT:-8000}` in the `CMD`. Don't
set `PORT` manually on the service — Railway's router expects its own
value.

## Environment variables

### `kindred-backend`

| Variable                              | Value                                                              |
|---------------------------------------|--------------------------------------------------------------------|
| `KINDRED_DATABASE_URL`                | `${{Postgres-EBkW.DATABASE_URL}}` (automatic reference)            |
| `KINDRED_OBJECT_STORE_ENDPOINT`       | `http://localhost:0` (InMemory store — see "Storage" below)        |
| `KINDRED_OBJECT_STORE_ACCESS_KEY`     | `unused`                                                           |
| `KINDRED_OBJECT_STORE_SECRET_KEY`     | `unused`                                                           |
| `KINDRED_OBJECT_STORE_BUCKET`         | `unused`                                                           |
| `KINDRED_FACILITATOR_SIGNING_KEY_HEX` | 64-char hex — `python3 -c 'import secrets;print(secrets.token_hex(32))'` |
| `KINDRED_ENV`                         | `prod`                                                             |
| `RAILWAY_DOCKERFILE_PATH`             | `Dockerfile`                                                       |

`config.py` auto-rewrites the sync `postgresql://` URL Railway provides
to `postgresql+asyncpg://` — no manual transformation needed.

### `kindred-web`

| Variable                  | Value                                                       |
|---------------------------|-------------------------------------------------------------|
| `NEXTAUTH_URL`            | `https://kindred-web-production.up.railway.app`             |
| `NEXTAUTH_SECRET`         | 64-char hex                                                 |
| `KINDRED_BACKEND_URL`     | `https://kindred-backend-production-4024.up.railway.app`    |
| `NEXT_TELEMETRY_DISABLED` | `1`                                                         |
| `RAILWAY_DOCKERFILE_PATH` | `Dockerfile`                                                |
| `PORT`                    | `3000`                                                      |
| `GITHUB_ID`               | (placeholder — create a GitHub OAuth App and set real ID)   |
| `GITHUB_SECRET`           | (placeholder — set alongside `GITHUB_ID`)                   |
| `GOOGLE_ID`               | (optional — Google OAuth button hidden if unset)            |
| `GOOGLE_SECRET`           | (optional — set alongside `GOOGLE_ID`)                      |

### `kindredformat`

| Variable                  | Value        |
|---------------------------|--------------|
| `RAILWAY_DOCKERFILE_PATH` | `Dockerfile` |
| `PORT`                    | `3000`       |

## Storage (current limitation)

The backend currently uses `InMemoryObjectStore` (triggered by endpoint
`:0` or `memory`). **Artifact bodies are lost on every redeploy.**
Metadata (in Postgres) survives; bodies don't.

Fix before serious use: wire S3, Cloudflare R2, or a Railway volume-backed
MinIO. Toggle by setting `KINDRED_OBJECT_STORE_ENDPOINT` to the real host
and populating access/secret keys. The `MinioObjectStore` adapter in
`backend/src/kindred/storage/object_store.py` is already wired.

## Deploy from scratch

### 1. Install prerequisites

```bash
brew install railway   # or curl -fsSL https://railway.com/install.sh | sh
railway login
```

### 2. Create project + Postgres

```bash
railway init --name kindred
railway link --project <project-id>
railway add --database postgres
```

Note: the CLI prints `> What do you need? Database` — that is a
**confirmation**, not a prompt. Running `railway add -d postgres`
a second time will create a **second** Postgres service. See lesson
(1) below.

### 3. Create the three app services (via GraphQL; CLI is interactive)

Railway CLI's `railway add -s <name>` is interactive and hard to drive
from scripts. Use the GraphQL API instead:

```bash
TOKEN=$(python3 -c "import json; print(json.load(open('$HOME/.railway/config.json'))['user']['token'])")
PROJECT_ID=<project-id>
ENV_ID=$(railway status --json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['environments']['edges'][0]['node']['id'])")

create_service() {
  local name=$1 root=$2
  local sid=$(curl -s -X POST https://backboard.railway.com/graphql/v2 \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    --data "{\"query\":\"mutation { serviceCreate(input: { projectId: \\\"$PROJECT_ID\\\", name: \\\"$name\\\" }) { id } }\"}" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['serviceCreate']['id'])")
  curl -s -X POST https://backboard.railway.com/graphql/v2 \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    --data "{\"query\":\"mutation { serviceInstanceUpdate(serviceId: \\\"$sid\\\", environmentId: \\\"$ENV_ID\\\", input: { rootDirectory: \\\"$root\\\" }) }\"}"
  echo "created $name ($sid) root=$root"
}

create_service kindred-backend /backend
create_service kindred-web     /web
create_service kindredformat   /kindredformat
```

### 4. Set env vars (see tables above)

Via `railway variables --set K=V` (CLI) or `variableUpsert` mutation.

### 5. Run migrations, deploy

```bash
# Run once from repo root — uploads the full tree; services pick their rootDir
railway service kindred-backend && railway up --detach
railway service kindred-web     && railway up --detach
railway service kindredformat   && railway up --detach
```

Each Dockerfile runs its own `alembic upgrade head` (backend) or `npm
run build` (web / kindredformat) inside the container. There's no
separate migration step.

### 6. Expose public domains

```bash
railway service kindred-backend && railway domain
railway service kindred-web     && railway domain
railway service kindredformat   && railway domain
```

### 7. Seed grimoires and smoke-test

```bash
export KINDRED_BACKEND_URL=https://<backend-domain>
export KINDRED_SEED_KEYFILE=/tmp/kindred-prod-seed.key
cd cli && uv run python ../scripts/seed_grimoires.py
```

Once the seed key is generated, save it — it's how you mint future
invites for kindreds you own.

---

## Seven failure modes we hit on first deploy

If you repeat this deploy on a fresh account, you will hit some of
these. They're all worth knowing.

### 1. `railway add -d postgres` runs successfully but looks like a prompt

The output `> What do you need? Database` is the TUI re-rendering the
auto-selected option. The command completes (exit 0) and creates the
service. If you re-run it to "get past the prompt," you create another
Postgres. We ended up with five before noticing. Always verify with
`railway status --json | grep Postgres`.

### 2. Empty services default to Railpack, not Docker

`railway add -s <name>` creates an empty service whose builder is
`RAILPACK`. Even a committed `railway.json` with `builder: DOCKERFILE`
is ignored until you explicitly set `RAILWAY_DOCKERFILE_PATH` as an
environment variable on the service. Do this immediately after creating
the service.

### 3. Monorepo context mismatch

When `railway up` runs from the repo root, the whole repo is uploaded.
Your Dockerfile's `COPY pyproject.toml ./` then fails because the path
is `backend/pyproject.toml`. Two options:

- Run `railway up` from the subdirectory (upload scoped to that dir) and
  set `RAILWAY_DOCKERFILE_PATH=Dockerfile`.
- Run `railway up` from the repo root and **set the service's
  `rootDirectory` via the `serviceInstanceUpdate` mutation** to scope
  Docker's build context to the subdirectory. This is what we do above.

### 4. `startCommand` in `railway.json` does NOT run under a shell

`${PORT:-8000}` is passed literally to uvicorn as the port argument, not
expanded. Symptom: uvicorn logs `Invalid value for '--port'` or simply
never binds. Fix: leave `startCommand` out of `railway.json` and rely on
the Dockerfile's `CMD sh -c "..."`, which **does** expand variables.

### 5. `uv run` at container startup is slow and pulls dev deps

`CMD uv run uvicorn …` triggers `uv sync` on each cold start, which
downloads the full lockfile including `ruff`, `pytest`, `aiosqlite`, etc.
The container takes ~40 seconds to become healthy and then gets killed
by the Railway healthcheck. Fix: `RUN uv sync --frozen --no-dev` at
build time, then `ENV PATH="/app/.venv/bin:$PATH"` and call `alembic`
and `uvicorn` directly in CMD.

### 6. Railway security scan blocks Next.js < 15.0.7

Railway's build pipeline runs Trivy or similar and fails the build when
Next.js 15.0.0 is pinned (CVE-2025-66478 CRITICAL, CVE-2025-55184 HIGH,
etc.). Fix: `npm install next@^15.0.7 --save` before deploying.

### 7. Object store guard gated on `env=dev`

`InMemoryObjectStore` was originally only selected when
`KINDRED_ENV == "dev"`. In production the backend fell through to
`MinioObjectStore` pointing at `http://localhost:80` and returned 500 on
artifact upload. Fix (now in `api/deps.py`): accept `endpoint=memory` or
endpoint ending in `:0` regardless of env, and document the "data lost
on redeploy" caveat above.

## Volume cleanup

Deleting a Postgres service via the dashboard or `serviceDelete`
mutation leaves the underlying **volume** in place by default (data
safety). If you accidentally spawned duplicate Postgres instances, clean
up their volumes separately:

```graphql
query {
  project(id: "<project-id>") {
    volumes { edges { node { id name volumeInstances { edges { node { serviceId } } } } } }
  }
}
```

Volumes with `serviceId: null` are orphaned and can be deleted via
`mutation { volumeDelete(volumeId: "...") }`. Always dump any data you
care about first.

## Post-launch follow-ups

1. **Switch to S3/R2 for artifact bodies.** InMemoryObjectStore loses data on redeploy.
2. **Real GitHub OAuth App.** The placeholders in `GITHUB_ID`/`GITHUB_SECRET` block Web UI sign-in.
3. **Custom domain.** `railway domain --custom kindred.sh` once DNS points at Railway.
4. **Publish `kindred-client` to PyPI.** Current invite flow uses `pip install ./cli`.
5. **Rotate the admin API token** used during initial setup if it was exposed during iteration.
6. **Schedule PITR drills.** Railway Postgres has automatic backups; verify restore works.
