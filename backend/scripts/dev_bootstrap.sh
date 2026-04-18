#!/usr/bin/env bash
# Bootstrap Kindred dev environment: start Postgres + MinIO via Docker, seed .env, run migrations
set -euo pipefail

cd "$(dirname "$0")/.."  # backend/

docker compose up -d
echo "Waiting for Postgres..."
for i in {1..30}; do
  if docker compose exec -T postgres pg_isready -U kindred >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

# Seed .env if not present
if [ ! -f .env ]; then
  cp .env.example .env
  KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
  # Replace placeholder key
  sed -i.bak "s/change-me-32-bytes-hex/$KEY/" .env && rm -f .env.bak
  echo "Generated fresh KINDRED_FACILITATOR_SIGNING_KEY_HEX in .env"
fi

uv run alembic upgrade head
echo ""
echo "Ready. Start server: uv run uvicorn kindred.api.main:app --reload"
