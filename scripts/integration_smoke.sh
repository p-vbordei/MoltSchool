#!/usr/bin/env bash
# End-to-end integration smoke test, designed to run on a clean
# checkout. Not wired into CI — it touches Docker and installs the CLI
# system-wide, which is intentional (we want it to mirror the
# first-user experience).
#
# Flow:
#   1. Bring up Postgres + MinIO via docker compose.
#   2. Install backend deps (uv) and run migrations.
#   3. Start the backend.
#   4. Seed the 5 flagship grimoires.
#   5. Mint an invite.
#   6. Install the CLI in a scratch venv + kin join + kin ask.
#   7. Tear everything down (unless KEEP=1).
#
# Usage:
#   ./scripts/integration_smoke.sh          # full cycle, tears down on exit
#   KEEP=1 ./scripts/integration_smoke.sh   # leave backend running at the end

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="${KINDRED_BACKEND_URL:-http://127.0.0.1:8000}"
KEEP="${KEEP:-0}"

SCRATCH="$(mktemp -d)"
BACKEND_PID=""

log() { printf "\n=== %s ===\n" "$*"; }

cleanup() {
    if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [[ "$KEEP" != "1" ]]; then
        ( cd "$REPO/backend" && docker compose down -v >/dev/null 2>&1 ) || true
        rm -rf "$SCRATCH"
    else
        echo "KEEP=1; leaving backend + compose stack running"
        echo "scratch dir: $SCRATCH"
    fi
}
trap cleanup EXIT

# 1. docker compose up
log "docker compose up (postgres + minio)"
( cd "$REPO/backend" && docker compose up -d )

# Wait for postgres
for i in {1..30}; do
    if ( cd "$REPO/backend" && docker compose exec -T postgres pg_isready -U kindred >/dev/null 2>&1 ); then
        echo "  postgres ready"
        break
    fi
    sleep 1
done

# 2. backend deps + migrations
log "uv sync + alembic upgrade head"
( cd "$REPO/backend" && uv sync )
( cd "$REPO/backend" && uv run alembic upgrade head )

# 3. start backend
log "starting backend"
(
    cd "$REPO/backend"
    nohup uv run uvicorn kindred.api.app:app --host 127.0.0.1 --port 8000 \
        > "$SCRATCH/backend.log" 2>&1 &
    echo $! > "$SCRATCH/backend.pid"
)
BACKEND_PID="$(cat "$SCRATCH/backend.pid")"

for i in {1..30}; do
    if curl -sf "$BACKEND_URL/v1/healthz" >/dev/null 2>&1; then
        echo "  backend ready (pid $BACKEND_PID)"
        break
    fi
    sleep 1
done
curl -sf "$BACKEND_URL/v1/healthz" >/dev/null || {
    echo "backend never became healthy; see $SCRATCH/backend.log"
    tail -n 50 "$SCRATCH/backend.log" || true
    exit 1
}

# 4. seed grimoires
log "seeding grimoires"
export KINDRED_BACKEND_URL="$BACKEND_URL"
export KINDRED_SEED_KEYFILE="$SCRATCH/seed.key"
python3 "$REPO/scripts/seed_grimoires.py"

# Verify the 5 kindreds exist
for slug in claude-code-patterns postgres-ops llm-eval-playbook agent-security kindred-patterns; do
    if curl -sf "$BACKEND_URL/v1/kindreds/$slug" >/dev/null; then
        echo "  [ok]   kindred $slug present"
    else
        echo "  [fail] kindred $slug missing"
        exit 1
    fi
done

# 5. mint invite
log "minting invite"
INVITE_URL="$(python3 "$REPO/scripts/mint_invite.py" --slug claude-code-patterns)"
echo "  invite: $INVITE_URL"

# 6. CLI flow in a scratch venv
log "CLI join + ask in scratch venv"
python3 -m venv "$SCRATCH/venv"
"$SCRATCH/venv/bin/pip" install --quiet --disable-pip-version-check "$REPO/cli"

HOME_BK="$HOME"
export HOME="$SCRATCH/home"
mkdir -p "$HOME"

"$SCRATCH/venv/bin/kin" join "$INVITE_URL" \
    --email "smoke@kindred.local" --name "Smoke Test User"
"$SCRATCH/venv/bin/kin" ask claude-code-patterns "tdd workflow" --k 1

export HOME="$HOME_BK"

log "integration smoke PASS"
