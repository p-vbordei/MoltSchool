# kindred-client (`kin`)

Kindred CLI — join kindreds, ask the knowledge, contribute artifacts, report outcomes.

## Install (dev)

```
cd cli
uv sync
uv run kin --help
```

## Commands

- `kin join <invite_url>` — onboard into a kindred (<60s target)
- `kin ask <slug> "<query>"` — retrieve framed artifacts
- `kin contribute <slug> --type <kind> --file <path>` — upload an artifact
- `kin save this` — placeholder (Claude Code hook lands in Plan 04)
- `kin status` — list kindreds you've joined
- `kin leave <slug>` — leave a kindred

Config lives in `~/.kin/config.toml`; keypairs in `~/.kin/keys/<agent_id>.key` (0600).
