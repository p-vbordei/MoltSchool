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

# Resolve path to the hook from this script's location.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
bash "$SCRIPT_DIR/../hooks/post_tool_use.sh"

FILE=$(ls "$HOME/.kin/history/"*.json | head -1)
grep -q "test-audit-uuid" "$FILE"
# Sentinel was rotated:
[[ ! -f "$HOME/.kin/last_audit_id" ]]
echo "OK"
