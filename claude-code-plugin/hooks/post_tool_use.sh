#!/usr/bin/env bash
# PostToolUse hook: detect "it worked" signals after a Bash run and stage an
# outcome record for `kin save` to pick up later.
#
# Heuristic: Bash tool with exit_code=0 AND output matches /passed|ok|SUCCESS|✓/i.
# Writes a JSON blob to $HOME/.kin/history/<timestamp>.json. Never fails the
# hook — we `exit 0` unconditionally so we don't block Claude Code.
set -euo pipefail

TOOL="${CLAUDE_TOOL_NAME:-}"
EXIT_CODE="${CLAUDE_TOOL_EXIT_CODE:-0}"
LAST_OUTPUT="${CLAUDE_TOOL_OUTPUT:-}"

if [[ "$TOOL" != "Bash" ]]; then
    exit 0
fi
if [[ "$EXIT_CODE" != "0" ]]; then
    exit 0
fi

# Grep for success markers. Suppress grep failure under `set -e`.
if ! printf '%s' "$LAST_OUTPUT" | grep -qE "(passed|SUCCESS|✓)"; then
    exit 0
fi

HIST_DIR="${HOME}/.kin/history"
mkdir -p "$HIST_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
SNIPPET_FILE="$(mktemp)"
trap 'rm -f "$SNIPPET_FILE"' EXIT
printf '%s' "$LAST_OUTPUT" | head -c 2000 > "$SNIPPET_FILE"

# Use python to JSON-encode the snippet safely.
AUDIT_ID_FILE="${HOME}/.kin/last_audit_id"
AUDIT_ID=""
if [[ -f "$AUDIT_ID_FILE" ]]; then
    AUDIT_ID="$(cat "$AUDIT_ID_FILE" 2>/dev/null || true)"
fi

python3 - "$TOOL" "$EXIT_CODE" "$TS" "$SNIPPET_FILE" "$HIST_DIR/$TS.json" "$AUDIT_ID" <<'PY' || true
import json, sys, pathlib
tool, exit_code, ts, snippet_path, out_path, audit_id = sys.argv[1:7]
snippet = pathlib.Path(snippet_path).read_text(errors="replace")
pathlib.Path(out_path).write_text(json.dumps({
    "tool": tool,
    "exit_code": exit_code,
    "timestamp": ts,
    "output_snippet": snippet,
    "audit_id": audit_id or None,
}))
PY

# Rotate the sentinel so one audit_id isn't credited twice.
rm -f "$AUDIT_ID_FILE" || true

exit 0
