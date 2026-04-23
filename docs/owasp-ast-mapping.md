# Kindred vs OWASP Agentic Skills Top 10

Mapping of Kindred's features to the [OWASP Agentic Skills Top 10](https://owasp.org/www-project-agentic-skills-top-10/)
risk catalog (AST01–AST10). Each row names the risk, the Kindred feature
that addresses it, and the code path where the control lives.

Where a control is partial or roadmapped, we say so — this doc is an
audit aid, not marketing.

| Risk                              | Kindred control                                                                 | Status    | Code / doc reference                                   |
|-----------------------------------|---------------------------------------------------------------------------------|-----------|--------------------------------------------------------|
| **AST01 — Malicious Skills**      | Ed25519 author signatures + threshold member *blessings* before an artifact is retrievable. A malicious author cannot self-publish past the bless threshold. | ✅ shipped | [`backend/src/kindred/services/artifacts.py`](../backend/src/kindred/services/artifacts.py), [`backend/src/kindred/services/blessings.py`](../backend/src/kindred/services/blessings.py) |
| **AST02 — Supply Chain Compromise** | Content-addressed artifact storage; signatures bind author pubkey to byte content; retrieval verifies signature. Tampering breaks the signature. No in-band update channel to compromise. | ✅ shipped | [`backend/src/kindred/crypto/`](../backend/src/kindred/crypto/), [`kindredformat/content/kaf-spec-0.1.md`](../kindredformat/content/kaf-spec-0.1.md) |
| **AST03 — Over-Privileged Skills** | **Not yet shipped.** Permission manifest per artifact (declared fs / network / env surface) is P0 roadmapped. Today KAF playbooks are text artifacts — no execution surface is exposed by Kindred itself; the consuming agent runtime governs privileges. | 🟡 roadmapped | [`docs/launch/competitor-learnings.md`](launch/competitor-learnings.md) §P0 |
| **AST04 — Insecure Metadata**     | KAF frontmatter is schema-validated on publish (title, author, created_at, expires_at, version). Author is pinned to a signing pubkey — cannot be spoofed post-sign. | ✅ shipped | [`backend/src/kindred/models/artifact.py`](../backend/src/kindred/models/artifact.py), [`kindredformat/content/kaf-spec-0.1.md`](../kindredformat/content/kaf-spec-0.1.md) |
| **AST05 — Unsafe Deserialization** | KAF is markdown with a typed frontmatter block; parsers reject unknown keys and exotic YAML tags. No code execution in the artifact pipeline. | ✅ shipped | [`backend/src/kindred/services/artifacts.py`](../backend/src/kindred/services/artifacts.py) |
| **AST06 — Weak Isolation**        | **Out of scope.** Kindred ships knowledge artifacts, not executable skills. Runtime isolation is the consuming agent runtime's job (Claude Code, Codex, etc.). Kindred's sanitiser strips injection-bearing content before the retrieved text reaches the model. | ⚪ n/a     | [`backend/src/kindred/facilitator/sanitizer.py`](../backend/src/kindred/facilitator/sanitizer.py) |
| **AST07 — Update Drift**          | Every artifact carries `expires_at`. Expired artifacts are filtered from retrieval until re-blessed. A consuming agent physically cannot run a stale playbook past its expiry. STSS flags this specific control as an open ecosystem gap; Kindred closes it. | ✅ shipped | [`backend/src/kindred/models/artifact.py`](../backend/src/kindred/models/artifact.py), [`backend/src/kindred/facilitator/librarian.py`](../backend/src/kindred/facilitator/librarian.py) |
| **AST08 — Poor Scanning**         | Injection corpus (55 adversarial cases) on CI; sanitiser blocks at retrieval. LLM "declared vs observed" pre-publish audit is P1 roadmapped (Vett/STSS pattern). | 🟢 shipped + 🟡 roadmapped | [`backend/tests/adversarial/`](../backend/tests/adversarial/), [`docs/launch/competitor-learnings.md`](launch/competitor-learnings.md) §P1 |
| **AST09 — No Governance**         | Kindreds *are* the governance primitive. Each kindred has a configurable bless threshold, member roster, audit log of every publish/bless/retrieval, and revocation via rotation. STSS flags AST09 as an ecosystem open item; Kindred closes it. | ✅ shipped | [`backend/src/kindred/services/audit.py`](../backend/src/kindred/services/audit.py), [`backend/src/kindred/models/kindred.py`](../backend/src/kindred/models/kindred.py) |
| **AST10 — Cross-Platform Reuse**  | **Partial.** KAF targets any MCP-capable runtime; today's CLI + plugin ship for Claude Code. Cross-agent `targets: [...]` frontmatter tag is P0 roadmapped so artifacts declare their tested runtimes explicitly (Codex, Cursor, Gemini CLI, MCP-generic). | 🟡 roadmapped | [`docs/launch/competitor-learnings.md`](launch/competitor-learnings.md) §P0 |

## Summary

| Status              | Count |
|---------------------|-------|
| ✅ Shipped          | 6     |
| 🟢 Partial (shipped + roadmap)        | 1 |
| 🟡 Roadmapped       | 2     |
| ⚪ Out of scope     | 1     |

Seven of ten OWASP Agentic Skills Top 10 controls are in `main` today.
Two more (AST03 permission manifest, AST10 cross-platform targets) are
P0 items for the launch post. AST06 (weak isolation) is architecturally
out of scope — Kindred signs knowledge, it does not run skills.

The two items STSS's Ken Huang explicitly flags as open gaps in the
ecosystem — **AST07 (update drift)** and **AST09 (no governance)** —
are both shipped and testable today.

## How to verify

- AST01, AST02: `./scripts/integration_smoke.sh` exercises sign →
  bless → retrieve → tamper-and-fail.
- AST04: `backend/tests/kaf/test_vectors.py` verifies the 12 spec
  vectors byte-for-byte.
- AST07: `backend/tests/unit/test_librarian.py` confirms expired
  artifacts are excluded from retrieval.
- AST08: `backend/tests/adversarial/` on every backend CI run — last
  count: 55/55 blocked.
- AST09: every publish, bless, and retrieval produces an `audit_event`
  row; see `backend/tests/unit/test_audit_race.py`.
