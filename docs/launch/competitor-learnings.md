# Competitor Learnings

Findings from a 5-agent parallel research pass (2026-04-23) across the
adjacent AI-agent-knowledge ecosystem. Inputs: Vett, STSS, Runics,
skills.sh, MindStudio Shared Business Brain, Claude Code plugin
marketplace, anthropics/knowledge-work-plugins, MCP Scorecard, Stacklok
ToolHive, Agent Trust Stack MCP, Mem0, VoltAgent awesome-agent-skills,
wshobson/agents.

This doc is input to launch copy and roadmap. It is not a spec.

## The wedge, confirmed

Every surveyed project ships agent knowledge or memory at scale. None
ships trust. The supply-chain attack surface is now public and exploited:

| Signal                                              | Date        |
|-----------------------------------------------------|-------------|
| Snyk ToxicSkills: 36% prompt injection, 13.4% critical, 1,467 malicious payloads across 3,984 skills | 2026        |
| ClawHavoc: 341 malicious skills flooded registries in 3 days | 2026-02 |
| Fake Postmark MCP key exfiltration                  | 2026-01     |
| CVE-2025-59536 + CVE-2026-21852 (RCE via `.claude/settings.json`) | 2026 |
| Trend Micro / Cato campaigns weaponizing Claude skills | 2026-03–04 |

Kindred's Ed25519 + threshold blessings + auto-expiry close exactly the
three gaps the community is informally asking for:

1. **Supply-chain RCE / unsigned code** — non-transitive trust per artifact.
2. **Silent skill drift** — expiry forces re-blessing, cannot run stale.
3. **No human review before install** — blessings are the review gate, in-protocol.

## User-desired features with open GitHub / HN issues

These are outstanding asks where Kindred already has the answer. Quote
them in launch copy.

- `skillsDirectories` config for shared team skill libs — [anthropics/claude-code#39403](https://github.com/anthropics/claude-code/issues/39403)
- Skill registry + pinning/updates — [opencode#8386](https://github.com/anomalyco/opencode/issues/8386)
- Desktop ↔ CLI skill sync — [anthropics/claude-code#20697](https://github.com/anthropics/claude-code/issues/20697)
- Signature verification on install — [vercel-labs/skills#617](https://github.com/vercel-labs/skills/issues/617) (unmerged for months)
- "Claude skills need a share button" — [every.to](https://every.to/vibe-check/vibe-check-claude-skills-need-a-share-button)

## Features to adopt

Ranked by effort × impact. Each entry names the source and the user
evidence that makes it worth doing.

### P0 — ship before launch post

- **One-line install UX.** `kin install <slug>` / `npx kindred add <slug>`.
  Users call skills.sh's `npx skills add` the single best thing about
  the ecosystem. Friction here sinks adoption.
  *Source: skills.sh HN threads, VoltAgent README.*
- **Permission manifest per artifact.** Declare filesystem paths, network
  endpoints, env vars read. Users approve capability surface, not opaque
  blobs. Vett ships this; community calls it out as the missing piece in
  Claude Code plugins (which execute arbitrary code with user privileges).
  *Source: Vett scanner output; Check Point CVE disclosures.*
- **Cross-agent compat tags on KAF.** Mark which runtimes each artifact
  targets (Claude Code, Codex, Cursor, Gemini CLI, MCP-generic). Expands
  addressable market beyond MCP-only.
  *Source: VoltAgent awesome-agent-skills frontmatter convention.*
- **OWASP Agentic Skills Top 10 mapping** in README + kindredformat.org.
  AST07 (version drift) and AST09 (missing governance) are flagged open
  by OWASP. Kindred closes both natively. Launch copy must name this.
  *Source: Ken Huang / OWASP Agentic Skills Top 10.*
- **Reserved names** (`kindred-official`, `anthropic-*`, `sigstore-*`) to
  prevent day-one impersonation — the Claude Code marketplace added this
  only after problems surfaced.
  *Source: code.claude.com/docs/en/plugin-marketplaces.*
- **Public trust badges on web UI.** At-a-glance: blessings-count,
  expiry-remaining, audit-status. Users trust layered signals more than
  one score. MCP Scorecard made this a category.
  *Source: mcp-scorecard.ai adoption.*

### P1 — next 2–4 weeks

- **Ranked retrieval on `kin ask`.** Current MCP fan-out is exact-slug.
  Add semantic search + rank formula `blessings × 0.7 + recency × 0.3`.
  Runics hit sub-60ms p50 over 15k skills — that is the bar.
  *Source: Runics / Cognium positioning.*
- **SHA pinning + separate `ref`/`sha` in KAF references.** Already how
  Claude Code private marketplaces survive "tag moves" attacks.
  *Source: Claude Code marketplace docs.*
- **Import-chain tracing surfaced in bless UI.** When a member blesses,
  show the full dep graph so blessings are informed, not blind.
  *Source: STSS (Ken Huang).*
- **LLM "declared vs observed" pre-publish audit.** Cheap sanity check:
  does the playbook's behavior match its description? Catches prompt
  injection hidden in docs.
  *Source: Vett + STSS both ship this.*
- **Graduated decay before expiry.** Relevance score drops with age so
  stale-but-not-dead playbooks surface with a warning rather than vanish
  at the cliff.
  *Source: Mem0 dynamic forgetting.*

### P2 — post-launch

- **Optional Rekor-style public transparency log.** Append-only log of
  signatures so external auditors can verify a kindred's history without
  trusting Kindred servers. Differentiates from Vett's centralized log.
  *Source: Sigstore Rekor.*
- **Bitcoin OpenTimestamps anchoring** on artifact hashes. Cheap,
  no-CA-needed provenance, strong netsec cred.
  *Source: Agent Trust Stack MCP (agent-trust-stack-mcp).*
- **Signed bundles** — "Platform team starter pack" ships as one signed
  bundle, not many individual artifacts.
  *Source: wshobson/agents plugin shape, Anthropic knowledge-work-plugins domain bundles.*
- **Quality gate CLI** on publish: frontmatter schema, description
  discoverability scoring, file-ref integrity, token budget ceilings.
  *Source: VoltAgent awesome-agent-skills gate tool.*
- **Verified-publisher badges** (GitHub org ownership proof) on top of
  Ed25519 — makes signatures human-legible, not just cryptographically
  valid.
  *Source: VoltAgent "official" badge, anthropics/claude-plugins-official.*

## Strategic risks

### Stacklok ToolHive — high risk

1,729 stars, 278 open issues, used at Fortune 500, founders co-created
Sigstore and Kubernetes. **Shipped "agent skills" in their Registry on
2026-04-06.** They are one release away from publishing signed skill
bundles with threshold trust — overlapping Kindred's wedge directly.

**Mitigation:** move fast on the *knowledge artifact* framing (KAF) and
the *member-blessing* story (web-of-trust, not CA-anchored). These are
the two things Stacklok is least likely to adopt — their whole stack
assumes Sigstore keyless CA trust. Lean on it in launch copy.

### MCP Scorecard — narrative risk

If Scorecard indexes Kindred artifacts and attaches its own opaque
trust score, we lose narrative control over our own trust signal.

**Mitigation:** publish a formal, cryptographic scoring spec early in
`kindredformat/`. Offer Scorecard a signed feed rather than letting
them scrape. Name our score; don't let a third party name it for us.

### Brand gravity risk — medium

skills.sh (91k skills indexed, Vercel brand, Snyk partnership) and
VoltAgent awesome-agent-skills (17.7k stars) own discovery. Anthropic
knowledge-work-plugins (11.5k stars) owns the knowledge-worker vertical.

**Mitigation:** position Kindred as the verification layer, not a
competing directory. "awesome-agent-skills discovers; Kindred verifies."
PR into their READMEs as the recommended signing flow for team-scoped
artifacts.

## What we are NOT going to do

- Compete on catalog size. skills.sh wins on scale; that is fine.
- Build a generic skill marketplace. Kindred's unit is a signed
  playbook/runbook in a trusted kindred, not a public skill.
- Replace Mem0. Agent private memory is complementary: Mem0 = derived,
  ephemeral, per-user; Kindred = authored, signed, team-scoped.
- Require Sigstore. Support it as an *optional* second signing mode for
  GitHub-native teams; keep Ed25519 + blessings as the default.

## Positioning one-liners (for launch copy)

- "Trust infrastructure for the agent-knowledge supply chain."
- "Signed, blessed, auto-expiring. Your team's runbooks, cryptographically."
- "awesome-agent-skills discovers skills. Kindred verifies yours."
- "The skill directory your CISO asks for when Snyk ToxicSkills lands in their inbox."
