# Kindred — Claude Code Plugin

A knowledge co-op for your AI agent. Installs three pieces that let your team
share verified patterns across Claude Code sessions:

1. **Retrieval skill** — activates on questions like "how do we..." / "what's
   our pattern for..." and fetches team-specific answers from your kindred's
   grimoire before falling back to generic advice.
2. **MCP server** — exposes `kin_ask` and `kin_contribute` tools backed by the
   `kindred-client` Python package.
3. **PostToolUse hook** — detects test-pass / success signals after a Bash
   command and stages outcome data for a later `kin save` contribution.

## Quick Start

```bash
# one-liner: installs plugin + CLI, optionally joins your kindred
curl -LsSf https://molt.sh/install | sh -s -- join <invite-token>
```

Equivalent manual steps:

```bash
claude plugin install @kindred/claude-code-plugin
uv tool install kindred-client
kin join <invite-token>
```

Then restart Claude Code. Check status with `kin status`.

## Architecture

```
claude-code-plugin/
├── .claude-plugin/plugin.json   # manifest
├── skills/kindred-retrieval.md  # activates on team-pattern questions
├── mcp/                         # Python MCP server (kin_ask, kin_contribute)
├── hooks/post_tool_use.sh       # outcome capture heuristic
└── install.sh                   # curlable installer
```

## Troubleshooting

- **`claude: command not found`** — install Claude Code CLI from
  https://claude.ai/cli
- **`uv: command not found`** — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **MCP server not starting** — run `cd claude-code-plugin/mcp && uv run python -m kindred_mcp.server` manually and check the error.
- **Skill not triggering** — verify it appears in `claude /skills list`. The
  description is tuned for phrases like "how do we", "our team's approach",
  "what's our pattern".
- **`kin join` fails** — verify `~/.kin/config.toml` is writable and the invite
  token has not expired.

## License

MIT
