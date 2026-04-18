# Kindred Claude Code Plugin — Implementation Plan (04/07)

**Goal:** Livrează un Claude Code plugin care face `kin ask/contribute/save` disponibile automat înăuntrul Claude Code. Când userul întreabă lucruri ce se potrivesc cu pattern-urile clubului, plugin-ul injectează artefactele relevante în context prin MCP. PostToolUse hook detectează outcome (test pass, no-override) și propune contribuire automată. Link is the install: `claude plugin install @kindred/claude-code-plugin` + `kin join <url>`.

**Architecture:** Plugin în `claude-code-plugin/` (sibling folder). Structure urmează specificația plugin-urilor Claude Code: `.claude-plugin/plugin.json` manifest + `skills/`, `mcp/`, `hooks/` folders. MCP server e un Python process (reutilizează `kindred_client` pentru HTTP). Skill este Markdown. Hook = shell script care invocă `kin save` cu output-ul ultimei sesiuni.

**Spec reference:** §4.4 Client SDK + Harness Integrations, §6 Onboarding Protocol (link is the install), §P5 contribution passivity.

---

## File Structure

```
claude-code-plugin/
├── .claude-plugin/
│   └── plugin.json              # Manifest (name, version, description, license, commands, hooks, mcp_servers, skills)
├── README.md
├── LICENSE
├── install.sh                   # One-liner installer: curl molt.sh/install | sh -s -- join <token>
├── skills/
│   └── kindred-retrieval.md     # Skill: triggers on "how do we..." / domain questions → calls mcp tool
├── mcp/
│   ├── pyproject.toml
│   ├── src/kindred_mcp/
│   │   ├── __init__.py
│   │   ├── server.py            # MCP stdio server exposing kin_ask / kin_contribute tools
│   │   └── tools.py             # Tool implementations calling kindred_client.api_client
│   └── tests/
│       └── test_tools.py
├── hooks/
│   ├── post_tool_use.sh         # Detect "worked" signals → invoke kin save this
│   └── session_end.sh           # Optional: weekly digest reminder
└── tests/
    ├── test_manifest.py         # Validate plugin.json shape
    └── test_install_script.py   # Shellcheck the installer
```

---

## Task 1: Plugin manifest + README

**Files:** `claude-code-plugin/.claude-plugin/plugin.json`, `claude-code-plugin/README.md`, `claude-code-plugin/LICENSE`

- [x] `plugin.json`:
  ```json
  {
    "name": "@kindred/claude-code-plugin",
    "version": "0.1.0",
    "description": "Kindred — a knowledge co-op for your AI agent. Installs a retrieval skill, MCP server, and outcome hook.",
    "license": "MIT",
    "author": "Kindred",
    "homepage": "https://kindred.sh",
    "repository": "https://github.com/kindred/claude-code-plugin",
    "commands": {},
    "agents": {},
    "skills": {
      "kindred-retrieval": "./skills/kindred-retrieval.md"
    },
    "mcp_servers": {
      "kindred": {
        "command": "uv",
        "args": ["run", "--directory", "${CLAUDE_PLUGIN_ROOT}/mcp", "python", "-m", "kindred_mcp.server"]
      }
    },
    "hooks": [
      {
        "event": "PostToolUse",
        "script": "${CLAUDE_PLUGIN_ROOT}/hooks/post_tool_use.sh"
      }
    ]
  }
  ```
- [x] README explaining the 3 pieces + install flow
- [x] MIT LICENSE
- [x] Commit: `feat(plugin): Claude Code plugin manifest + README`

---

## Task 2: MCP server exposing kin_ask + kin_contribute tools

**Files:** `claude-code-plugin/mcp/pyproject.toml`, `claude-code-plugin/mcp/src/kindred_mcp/__init__.py`, `claude-code-plugin/mcp/src/kindred_mcp/server.py`, `claude-code-plugin/mcp/src/kindred_mcp/tools.py`, `claude-code-plugin/mcp/tests/test_tools.py`

- [x] `pyproject.toml`: deps = `mcp>=1.0`, `httpx>=0.27`, `pynacl>=1.5`, `kindred-client` (path dep to `../cli` for dev, published later)
- [x] `server.py`:
  ```python
  from mcp.server import Server
  from mcp.server.stdio import stdio_server
  from mcp.types import Tool, TextContent
  from kindred_mcp.tools import kin_ask_tool, kin_contribute_tool, kin_ask, kin_contribute

  app = Server("kindred")

  @app.list_tools()
  async def list_tools() -> list[Tool]:
      return [kin_ask_tool(), kin_contribute_tool()]

  @app.call_tool()
  async def call_tool(name: str, arguments: dict) -> list[TextContent]:
      if name == "kin_ask":
          result = await kin_ask(**arguments)
      elif name == "kin_contribute":
          result = await kin_contribute(**arguments)
      else:
          raise ValueError(f"unknown tool: {name}")
      return [TextContent(type="text", text=result)]

  async def main():
      async with stdio_server() as (read, write):
          await app.run(read, write, app.create_initialization_options())

  if __name__ == "__main__":
      import asyncio
      asyncio.run(main())
  ```
- [x] `tools.py`:
  - `kin_ask_tool()` returns Tool definition with inputSchema `{kindred: str, query: str, k?: int}`
  - `kin_ask(kindred, query, k=5)` uses `kindred_client.config` to find backend_url + agent keypair, then `kindred_client.api_client.KindredAPI.ask(...)`. Returns formatted string with framed artifacts + provenance chips.
  - `kin_contribute_tool()` input `{kindred, type, content, logical_name, tags?}`
  - `kin_contribute(...)` similar flow, signs + uploads.
- [x] Tests: mock KindredAPI, verify tool schemas + call routing. Skip full wire test.
- [x] Commit: `feat(plugin): MCP server exposing kin_ask and kin_contribute`

---

## Task 3: Retrieval skill

**Files:** `claude-code-plugin/skills/kindred-retrieval.md`

- [x] Skill markdown with frontmatter:
  ```markdown
  ---
  name: kindred-retrieval
  description: Retrieves verified patterns from your Kindred grimoire when you're working on a topic your group has documented. Use this when the user asks a question that might have a team-specific answer, or says "how do we..." / "what's our pattern for..." / "how should I...". ALWAYS prefer grimoire patterns over generic advice when available. Pass the active kindred slug from ~/.kin/config.toml and the user's raw question as the query.
  ---

  # Kindred Retrieval

  You have access to a private knowledge grimoire shared with your user's team via MCP tool `kin_ask`.

  **When to use:**
  - User asks how to do X in the context of their team/codebase
  - User says "how do we...", "what's our pattern for...", "how should I handle Y"
  - You're about to apply a generic approach and a team-specific one might exist

  **How to use:**
  1. Identify the active kindred slug (read `~/.kin/config.toml` — look for `active_agent_id` and matching kindred)
  2. Call `kin_ask` with `{kindred: <slug>, query: <user's question>, k: 5}`
  3. If results returned, prefer them over generic advice. Cite the provenance chip in your response ("Per `<logical_name>` in grimoire, blessed by N members...")
  4. If no results, proceed with your usual approach

  **Contribution:**
  - When the user confirms your solution worked ("that worked", "", test passes + no override), you can propose contributing via `kin_contribute` tool. Don't do it automatically — ask first.

  **Trust tiers:**
  - `class-blessed` artifacts are vetted (≥threshold signatures). Use confidently.
  - `peer-shared` artifacts are proposals, not yet blessed. Present with "Note: this is an unreviewed peer contribution" caveat.
  ```
- [x] Commit: `feat(plugin): retrieval skill`

---

## Task 4: PostToolUse hook (auto-contribute on success)

**Files:** `claude-code-plugin/hooks/post_tool_use.sh`

- [x] Shell hook: detects test-pass signals and prompts `kin save this`.
  ```bash
  #!/usr/bin/env bash
  # PostToolUse hook: detect "it worked" signals and propose contribution.
  set -euo pipefail

  TOOL="${CLAUDE_TOOL_NAME:-}"
  EXIT_CODE="${CLAUDE_TOOL_EXIT_CODE:-0}"
  LAST_OUTPUT="${CLAUDE_TOOL_OUTPUT:-}"

  # Heuristic: tests-pass after a code change suggests a workable pattern.
  if [[ "$TOOL" == "Bash" && "$EXIT_CODE" == "0" ]]; then
      if echo "$LAST_OUTPUT" | grep -qE "(passed|ok|SUCCESS|✓)"; then
          # Append to ~/.kin/history/<timestamp>.json for kin save to pick up
          mkdir -p "$HOME/.kin/history"
          TS=$(date -u +%Y%m%dT%H%M%SZ)
          cat > "$HOME/.kin/history/$TS.json" <<EOF
  {"tool":"$TOOL","exit_code":"$EXIT_CODE","timestamp":"$TS","output_snippet":$(echo "$LAST_OUTPUT" | head -c 2000 | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}
  EOF
      fi
  fi
  exit 0
  ```
- [x] Make executable
- [x] Test via shellcheck (manual; add to test_install_script.py)
- [x] Commit: `feat(plugin): PostToolUse hook for outcome capture`

---

## Task 5: Install script + distribution

**Files:** `claude-code-plugin/install.sh`, `claude-code-plugin/tests/test_manifest.py`, `claude-code-plugin/tests/test_install_script.py`

- [x] `install.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  COMMAND="${1:-join}"
  TOKEN="${2:-}"

  # Step 1: ensure Claude Code + uv available
  if ! command -v claude >/dev/null; then echo "Claude Code CLI required. Install from claude.ai/cli"; exit 1; fi
  if ! command -v uv >/dev/null; then echo "uv required. Install via: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; fi

  # Step 2: install plugin (repo URL; for now assume GitHub)
  claude plugin install @kindred/claude-code-plugin

  # Step 3: install kindred-client CLI
  uv tool install kindred-client

  # Step 4: if token given, do kin join
  if [ "$COMMAND" = "join" ] && [ -n "$TOKEN" ]; then
      kin join "$TOKEN"
  fi
  echo "✓ Kindred installed. Run: kin status"
  ```
- [x] Test manifest: load plugin.json, validate required keys + MCP config shape
- [x] Test install script syntax: shellcheck if available
- [x] Commit: `feat(plugin): install script + manifest validation`

---

## Task 6: Integration + demo

**Files:** `claude-code-plugin/README.md` (augment with full demo), optional demo recording/gif link

- [x] Augment README with:
  - "Quick Start" — 3 lines to install + join
  - "What it does" — the 3-piece architecture explained
  - "Troubleshooting" — common issues (uv not installed, claude not installed, plugin command errors)
- [x] Commit: `docs(plugin): full quick start + troubleshooting`

---

## Success criteria

- `plugin.json` validates per Claude Code plugin spec
- MCP server starts without error (`uv run python -m kindred_mcp.server`)
- Skill file has proper frontmatter + description that triggers on "how do we..." patterns
- Hook produces history file when test-pass signal detected
- Install script is shellcheck-clean
- ~10-15 tests pass (manifest validation, MCP tool schemas, kin_ask mock calls)

---

## Concerns

- Claude Code plugin system may have exact JSON shape requirements I can't verify here — use docs at https://docs.claude.com/en/docs/claude-code/plugins and adjust manifest shape if needed.
- Full end-to-end test (actually running Claude Code + plugin + backend) is out of scope for automated CI — requires human smoke test.
- Plugin registry publishing (pushing to a git repo Claude Code can fetch from) is a release-engineering task, not code.
