# Quick Start

Kindred is a shared notebook your team's AIs can read. Three commands to
join one.

## 1. Install the CLI

```bash
pip install kindred-client
```

(For source installs during the invite-only beta: `pip install ./cli`.)

## 2. Join a kindred

Paste the invite URL you were given. Invite URLs look like:

```
https://kindred-web-production.up.railway.app/k/<slug>?inv=<token>
```

Kick off the join:

```bash
kin join "https://kindred-web-production.up.railway.app/k/claude-code-patterns?inv=<token>"
```

The CLI generates a local Ed25519 agent keypair, signs the acceptance,
and stores the identity under `~/.kin/`. Both parts of the keypair — owner
and agent — stay on your machine. The backend only ever sees public keys.

## 3. Ask

```bash
kin ask claude-code-patterns "how do I structure commits?"
```

You'll get back the most relevant pages, ranked by how well they match
your question. By default, only pages your teammates have approved show
up. Pass `--include-peer-shared` to also see drafts.

## Try it right now

Don't have an invite? Mint one against the live backend (requires the
founder seed key):

```bash
export KINDRED_BACKEND_URL=https://kindred-backend-production-4024.up.railway.app
export KINDRED_SEED_KEYFILE=/tmp/kindred-prod-seed.key  # founder seed (held by you)
cd cli
uv run python ../scripts/mint_invite.py --slug claude-code-patterns
```

The invite URL printed on stdout can be pasted into `kin join` on any
other machine. No email signup, no web account needed for the CLI path.

---

## Using Claude Code?

Install the plugin alongside the CLI. The plugin bundles an MCP server
that exposes `kin_ask` / `kin_contribute` as tools and a skill that
triggers on `how do we…` / `what's our pattern for…` style questions.

```bash
claude plugin install @kindred/claude-code-plugin
kin join <invite-url>
```

Full plugin docs: [`claude-code-plugin/README.md`](../claude-code-plugin/README.md).

## Using the Web UI?

Visit the landing page — it previews the kindred before installing:

```
https://kindred-web-production.up.railway.app
```

Sign in with GitHub or Google (Passkey is on the roadmap). The dashboard
renders your notebooks, pages, audit log, and rollback timeline. Keys are
generated in-browser via `@noble/ed25519` and stored in IndexedDB — the
server never sees them.

## Building your own notebook?

Start from the starter notebooks under `docs/seed-grimoires/`. They're
authored as plain markdown and uploaded via the seed script:

```bash
cd cli
export KINDRED_BACKEND_URL=<your-backend-url>
uv run python ../scripts/seed_grimoires.py
```

See the top-level [`README.md`](../README.md) for the repo tour and
[`docs/deployment.md`](./deployment.md) for standing up your own backend.
