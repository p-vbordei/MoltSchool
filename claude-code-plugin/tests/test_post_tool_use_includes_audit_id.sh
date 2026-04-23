#!/usr/bin/env bash
set -euo pipefail

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP"
mkdir -p "$HOME/.kin"
echo "test-audit-uuid" > "$HOME/.kin/last_audit_id"

export CLAUDE_TOOL_NAME=Bash
export CLAUDE_TOOL_EXIT_CODE=0
export CLAUDE_TOOL_OUTPUT="12 passed"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
bash "$SCRIPT_DIR/../hooks/post_tool_use.sh"

FILE=$(ls "$HOME/.kin/history/"*.json | head -1)
grep -q "test-audit-uuid" "$FILE"
[[ ! -f "$HOME/.kin/last_audit_id" ]]

# --- No-sentinel path: hook runs without a prior ask -----------------------
# Clear history and ensure no sentinel exists.
rm -rf "$HOME/.kin/history"
rm -f "$HOME/.kin/last_audit_id"
# Sleep one second so the new history file has a different timestamp
# (the hook uses `date -u +%Y%m%dT%H%M%SZ`, second precision).
sleep 1
bash "$SCRIPT_DIR/../hooks/post_tool_use.sh"
FILE2=$(ls "$HOME/.kin/history/"*.json | head -1)
grep -q '"audit_id": null' "$FILE2"

echo "OK"
