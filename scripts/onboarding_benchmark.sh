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
#   * `date +%s%N` returns nanoseconds — Linux with GNU coreutils,
#     or macOS ≥14.1 (BSD date gained %N in FreeBSD 14.1). Older macOS
#     returns a literal "N" which breaks the ms arithmetic below.
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

# --- Preamble: install CLI (not part of TTFUR wall-clock) -----------------

pip install --quiet --disable-pip-version-check "$REPO/cli" >/dev/null \
    || die "pip install of local cli failed"
ok "installed cli from $REPO/cli"

# --- TTFUR wall-clock: join -> ask -> report success ----------------------

START_NS=$(date +%s%N)

kin join "$INVITE_URL" --email "bench@kindred.local" --name "Bench User" \
    || die "kin join failed"
ok "joined kindred"

# --peer-shared: freshly seeded artifacts are unblessed until members bless them;
# the benchmark measures TTFUR for a real joiner, which includes peer-shared hits.
ASK_JSON=$(kin ask "$KINDRED_SLUG" "tdd workflow" --k 1 --peer-shared --json) \
    || die "kin ask failed"

AUDIT_ID=$(python3 -c "import json,sys; print(json.loads(sys.stdin.read())['audit_id'])" <<<"$ASK_JSON")
CHOSEN_CID=$(python3 -c "import json,sys; arts=json.loads(sys.stdin.read()).get('artifacts') or []; print(arts[0]['content_id'] if arts else '')" <<<"$ASK_JSON")

if [[ -z "$CHOSEN_CID" ]]; then
    die "ask returned no artifacts — nothing to report"
fi

kin report "$AUDIT_ID" success --chose "$CHOSEN_CID" \
    || die "kin report failed"
ok "reported outcome=success"

END_NS=$(date +%s%N)
ELAPSED_MS=$(( (END_NS - START_NS) / 1000000 ))
ELAPSED_S=$(( ELAPSED_MS / 1000 ))

echo ""
echo "================================================"
echo "  TTFUR: ${ELAPSED_MS}ms (${ELAPSED_S}s)  (budget ${BUDGET_SECONDS}s)"
echo "================================================"

if (( ELAPSED_S > BUDGET_SECONDS )); then
    echo "FAIL: TTFUR exceeded budget"
    exit 1
fi

echo "PASS"
