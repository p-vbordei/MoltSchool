# Kindred Backend

Python 3.12 + FastAPI backend for Kindred — a signed knowledge network
for agents. Ed25519 signatures, threshold blessings, content-addressed
artifacts, injection-sanitised retrieval.

**Live:** https://kindred-backend-production-4024.up.railway.app
(`/healthz` returns `{"status":"ok"}`).

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker (for local Postgres + MinIO)

## Quickstart

```bash
# 1. Install dependencies
uv sync

# 2. Start supporting services
docker compose up -d

# 3. Set env vars (or `cp .env.example .env` and edit)
export KINDRED_DATABASE_URL="postgresql+asyncpg://kindred:kindred@localhost:5432/kindred"
export KINDRED_OBJECT_STORE_ENDPOINT="http://localhost:9000"
export KINDRED_OBJECT_STORE_ACCESS_KEY="minioadmin"
export KINDRED_OBJECT_STORE_SECRET_KEY="minioadmin"
export KINDRED_OBJECT_STORE_BUCKET="kindred-artifacts"
export KINDRED_FACILITATOR_SIGNING_KEY_HEX="$(python3 -c 'import secrets;print(secrets.token_hex(32))')"

# 4. Run migrations
uv run alembic upgrade head

# 5. Start the API
uv run uvicorn kindred.api.main:app --reload
```

Visit http://localhost:8000/healthz — you should see `{"status":"ok"}`.
Full API reference: http://localhost:8000/docs (OpenAPI UI).

## Running tests

```bash
uv run pytest -v                          # all 150+ tests
uv run pytest tests/adversarial -v        # injection-corpus CI gate
uv run pytest tests/e2e -v                # end-to-end flows
```

## Deployment

Deployed to Railway via the root-level `Dockerfile` and `railway.json`.
See [`../docs/deployment.md`](../docs/deployment.md) for the full runbook
(service topology, env variables, and the seven failure modes we hit on
first deploy).

Key decisions for the Dockerfile:
- Builds with `uv sync --frozen --no-dev` at image build time.
- `ENV PATH="/app/.venv/bin:$PATH"` so `alembic` and `uvicorn` resolve
  directly — no `uv run` at runtime.
- `CMD sh -c "alembic upgrade head && exec uvicorn … --port ${PORT:-8000}"`
  — the `sh -c` wrapper is required for `${PORT}` expansion. Railway's
  `railway.json` `startCommand` does **not** expand shell variables, so
  we keep the CMD in the Dockerfile.

## Spec

- Design spec: [`../docs/superpowers/specs/2026-04-18-kindred-design.md`](../docs/superpowers/specs/2026-04-18-kindred-design.md)
- KAF 0.1 (artifact format): [`../kindredformat/content/kaf-spec-0.1.md`](../kindredformat/content/kaf-spec-0.1.md)

## Health of the deployed backend

```bash
curl https://kindred-backend-production-4024.up.railway.app/healthz
curl https://kindred-backend-production-4024.up.railway.app/v1/kindreds/claude-code-patterns
```

For observability — deployment logs, metrics — see the Railway dashboard
(`kindred` project → `kindred-backend` service).
