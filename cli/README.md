# kindred-client (`kin`)

The `kin` command-line tool for Kindred — your team's shared notebook your
AI reads. Join a notebook, ask questions of it, add new pages.

## Install (dev)

```
cd cli
uv sync
uv run kin --help
```

## Commands

- `kin join <invite_url>` — join your team's shared notebook (<60s target)
- `kin ask <slug> "<query>"` — ask a question; get the most relevant pages back
- `kin contribute <slug> --type <kind> --file <path>` — add a page to the notebook
- `kin save this` — placeholder (Claude Code hook lands in Plan 04)
- `kin status` — list the notebooks you've joined
- `kin leave <slug>` — leave a notebook

Config lives in `~/.kin/config.toml`; keypairs in `~/.kin/keys/<agent_id>.key` (0600).
