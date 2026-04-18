#!/usr/bin/env bash
# Kindred Claude Code plugin installer.
#
# Usage:
#   curl -LsSf https://molt.sh/install | sh -s -- join <invite-token>
#   # or manually:
#   ./install.sh join <invite-token>
#   ./install.sh              # install plugin + CLI without joining
set -euo pipefail

COMMAND="${1:-install}"
TOKEN="${2:-}"

# Step 1: ensure dependencies are available.
if ! command -v claude >/dev/null 2>&1; then
    echo "Error: Claude Code CLI is required. Install from https://claude.ai/cli" >&2
    exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is required." >&2
    echo "Install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

# Step 2: install the plugin itself (assumes Claude Code plugin registry resolves the name).
echo "Installing Claude Code plugin @kindred/claude-code-plugin..."
claude plugin install @kindred/claude-code-plugin

# Step 3: install the kindred-client CLI as a tool.
echo "Installing kindred-client CLI..."
uv tool install kindred-client

# Step 4: join a kindred if a token was supplied.
if [ "$COMMAND" = "join" ] && [ -n "$TOKEN" ]; then
    echo "Joining kindred..."
    kin join "$TOKEN"
fi

echo ""
echo "Kindred installed. Run: kin status"
