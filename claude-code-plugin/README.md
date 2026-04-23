# Kindred — Claude Code Plugin

Your team's shared notebook, wired into Claude Code. Installs three pieces
that let every teammate's Claude Code read and write the same notes,
automatically.

## Quick Start

```bash
# one-liner: installs plugin + CLI, optionally joins your kindred
curl -LsSf https://molt.sh/install | sh -s -- join <invite-token>
```

Three equivalent manual steps:

```bash
claude plugin install @kindred/claude-code-plugin   # plugin → MCP + skill + hook
uv tool install kindred-client                      # CLI: kin ask/contribute/save
kin join <invite-token>                             # enroll this machine
```

Then restart Claude Code. Check status with `kin status`.

## What it does

The plugin is three pieces working together:

1. **Retrieval skill** (`skills/kindred-retrieval.md`) — activates on
   "how do we...", "what's our pattern for...", "our team's approach to...".
   When triggered, it calls the MCP tool to fetch the relevant pages from
   your team's notebook before falling back to generic advice.
2. **MCP server** (`mcp/`) — a Python stdio process exposing two tools:
   - `kin_ask(kindred, query, k)` — ask the notebook a question; get the
     most relevant pages back, each with the teammate who wrote it.
   - `kin_contribute(kindred, type, content, logical_name, tags)` — add a
     new page (shared as a draft until a teammate approves it).
   Both wrap `kindred_client.api_client.KindredAPI`, so auth + signing reuse
   the same keystore the CLI uses (`~/.kin/keys/`).
3. **PostToolUse hook** (`hooks/post_tool_use.sh`) — after every Bash tool
   run that exited 0 and looked like a success ("passed", "SUCCESS", "✓"),
   stage a JSON record under `~/.kin/history/`. `kin save this` picks the
   newest one and turns it into a contribution.

## Architecture

```
claude-code-plugin/
├── .claude-plugin/plugin.json   # manifest (name, mcp_servers, skills, hooks)
├── skills/kindred-retrieval.md  # activates on team-pattern questions
├── mcp/                         # Python MCP server (kin_ask, kin_contribute)
│   ├── pyproject.toml           # kindred-client as path dep → ../../cli
│   ├── src/kindred_mcp/{server,tools}.py
│   └── tests/test_tools.py
├── hooks/post_tool_use.sh       # outcome capture heuristic
├── tests/                       # manifest + install script validation
└── install.sh                   # curlable installer
```

## Troubleshooting

- **`claude: command not found`** — install Claude Code CLI from
  https://claude.ai/cli, then re-run the installer.
- **`uv: command not found`** — `curl -LsSf https://astral.sh/uv/install.sh | sh`
  and restart your shell.
- **MCP server not starting** — run it manually to see the error:
  `cd claude-code-plugin/mcp && uv run python -m kindred_mcp.server`.
  The process should block on stdin (that's correct — MCP uses stdio JSON-RPC).
- **Skill not triggering** — verify it appears in `claude /skills list`. The
  description is tuned for phrases like "how do we", "our team's approach",
  "what's our pattern". You can also invoke it by name: `claude /skills run kindred-retrieval`.
- **`kin join` fails** — confirm `~/.kin/config.toml` is writable and the
  invite token has not expired. `kin status` shows the current joined kindreds.
- **Hook not firing** — Claude Code passes `CLAUDE_TOOL_NAME`,
  `CLAUDE_TOOL_EXIT_CODE`, and `CLAUDE_TOOL_OUTPUT` to PostToolUse hooks.
  If the env var names differ in your Claude Code version, update the top of
  `hooks/post_tool_use.sh`.

## Development

```bash
# Run MCP tests + manifest/install validation
cd claude-code-plugin/mcp && uv run pytest -v
```

## License

MIT
