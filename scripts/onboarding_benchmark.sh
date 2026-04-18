#!/usr/bin/env bash
# Onboarding benchmark — measures the wall-clock time from
# "fresh install of the CLI" to "first successful ask".
#
# Success criterion: elapsed < 60 seconds.
#
# Assumptions (the caller is responsible for these):
#   * A Kindred backend is already listening at $KINDRED_BACKEND_URL.
#   * The backend is empty OR already contains the `claude-code-patterns`
#     kindred (the seed script can populate it).
#   * `python3` and `pip` are on PATH.
#
# Usage:
#   ./scripts/onboarding_benchmark.sh [--invite <url>]
#
# If --invite is omitted, the script issues a fresh invite via the founder
# pubkey persisted by scripts/seed_grimoires.py (~/.kin/seed.key).

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="${KINDRED_BACKEND_URL:-http://localhost:8000}"
BUDGET_SECONDS="${ONBOARDING_BUDGET_SECONDS:-60}"
KINDRED_SLUG="${KINDRED_SLUG:-claude-code-patterns}"
INVITE_URL=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --invite) INVITE_URL="$2"; shift 2 ;;
        --budget) BUDGET_SECONDS="$2"; shift 2 ;;
        --slug)   KINDRED_SLUG="$2"; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

# --- Helpers ---------------------------------------------------------------

die() { echo "ERR: $*" >&2; exit 1; }
ok()  { printf "  [ok]  %s\n" "$*"; }

# --- Preflight -------------------------------------------------------------

command -v python3 >/dev/null || die "python3 not on PATH"
command -v pip >/dev/null || command -v pip3 >/dev/null || die "pip not on PATH"

if ! curl -sf "$BACKEND_URL/healthz" >/dev/null 2>&1 \
     && ! curl -sf "$BACKEND_URL/v1/healthz" >/dev/null 2>&1; then
    die "backend not reachable at $BACKEND_URL (expected /healthz or /v1/healthz)"
fi
ok "backend reachable at $BACKEND_URL"

# Scratch directory so repeated runs don't carry state.
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT
export HOME="$SCRATCH"   # kin stores config under $HOME/.kin/
export KINDRED_BACKEND_URL="$BACKEND_URL"

# --- If no invite supplied, mint one ---------------------------------------

if [[ -z "$INVITE_URL" ]]; then
    echo "No --invite given; minting one via mint_invite.py..."
    INVITE_URL="$(python3 "$REPO/scripts/mint_invite.py" --slug "$KINDRED_SLUG")"
    ok "minted invite: $INVITE_URL"
fi

# --- Benchmark -------------------------------------------------------------

START="$(date +%s)"

pip install --quiet --disable-pip-version-check "$REPO/cli" >/dev/null \
    || die "pip install of local cli failed"
ok "installed cli from $REPO/cli"

kin join "$INVITE_URL" --email "bench@kindred.local" --name "Bench User" \
    || die "kin join failed"
ok "joined kindred"

kin ask "$KINDRED_SLUG" "tdd workflow" --k 1 \
    || die "kin ask failed"
ok "first ask returned"

END="$(date +%s)"
ELAPSED=$(( END - START ))

echo ""
echo "================================================"
echo "  Onboarding elapsed: ${ELAPSED}s  (budget ${BUDGET_SECONDS}s)"
echo "================================================"

if (( ELAPSED > BUDGET_SECONDS )); then
    echo "FAIL: onboarding exceeded budget"
    exit 1
fi

echo "PASS"
