#!/usr/bin/env bash
# Thin wrapper around seed_grimoires.py so CI and docs can invoke it
# without remembering Python path.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${KINDRED_BACKEND_URL:=http://localhost:8000}"
export KINDRED_BACKEND_URL

# Prefer the cli package's venv if present, else fall back to system python.
if [[ -x "$REPO/cli/.venv/bin/python" ]]; then
    PYTHON="$REPO/cli/.venv/bin/python"
else
    PYTHON="${PYTHON:-python3}"
fi

echo "Seeding grimoires against $KINDRED_BACKEND_URL ..."
exec "$PYTHON" "$REPO/scripts/seed_grimoires.py"
