# Kindred KAF Spec + Launch Package — Implementation Plan (07/07)

**Goal:** Livrează KAF (Kindred Artifact Format) 0.1 spec public la `kindredformat.org`, 5 flagship seed grimoires cu conținut real, CI benchmark pentru onboarding <60s, transparency page cu injection metrics, docs complete (Quick Start, Threat Model, KAF Spec) și launch checklist.

**Architecture:** Static site Next.js separat în `kindredformat/` pentru spec + `docs/launch/` pentru seed grimoire content (markdown). CI workflow nou pentru onboarding benchmark. `BENCHMARK.md` publishable cu rezultate.

**Spec reference:** §9 MVP (KAF 0.1 spec publicat), §11 Success Criteria (onboarding <60s, injection 100%), §16 Launch Checklist.

---

## File Structure

```
kindredformat/                        # Static spec site (kindredformat.org)
├── package.json
├── next.config.mjs
├── src/app/
│   ├── layout.tsx
│   ├── page.tsx                      # KAF 0.1 spec (long markdown rendered)
│   ├── examples/page.tsx             # Annotated YAML examples
│   └── implementers/page.tsx         # Guide for external KAF implementers
└── content/
    ├── kaf-spec-0.1.md
    ├── kaf-examples.md
    └── kaf-implementers-guide.md

docs/
├── quick-start.md                    # 1-page quickstart
├── threat-model.md                   # Full threat model + mitigations
├── transparency.md                   # Injection block metrics (updated by CI)
└── seed-grimoires/
    ├── claude-code-patterns/
    │   ├── README.md
    │   ├── claude_md.md
    │   ├── routine-tdd-per-task.md
    │   ├── routine-git-commits-per-task.md
    │   └── skill-ref-superpowers.json
    ├── postgres-ops/
    │   ├── README.md
    │   ├── routine-handle-bloat.md
    │   ├── routine-migration-structure.md
    │   └── routine-backup-restore.md
    ├── llm-eval-playbook/
    │   ├── README.md
    │   ├── routine-benchmark-harness.md
    │   └── routine-cost-tracking.md
    ├── agent-security/
    │   ├── README.md
    │   ├── routine-injection-defense.md
    │   └── routine-sandboxing.md
    └── kindred-patterns/              # Meta: patterns for building Kindred itself
        ├── README.md
        ├── routine-backend-tdd-style.md
        └── claude_md.md

scripts/
├── seed_grimoires.sh                 # Populates a running backend with the 5 grimoires
└── onboarding_benchmark.sh           # Times click-to-first-query

.github/workflows/
└── launch-benchmark.yml              # Runs onboarding benchmark + updates transparency page
```

---

## Task 1: KAF 0.1 spec content

**Files:** `kindredformat/content/kaf-spec-0.1.md`, `kindredformat/content/kaf-examples.md`, `kindredformat/content/kaf-implementers-guide.md`

- [ ] `kaf-spec-0.1.md` — full canonical spec:
  - Abstract, conformance language (MUST/SHOULD/MAY per RFC 2119)
  - Artifact envelope: required fields (`kaf_version`, `type`, `id`, `author`, `author_sig`, `valid_from`, `valid_until`, `logical_name`)
  - Optional fields: `blessed_sigs`, `tags`, `outcome_stats`, `test_harness`, `superseded_by`
  - Types enumeration: `claude_md`, `routine`, `skill_ref`, `repo_ref` (v1), `conversation_distilled` (v1), `benchmark_ref` (v1)
  - Content ID calculation: canonical JSON (sort keys, no whitespace, UTF-8 no ASCII escape) + SHA-256 → `sha256:<hex>`
  - Signature algorithm: Ed25519; sign `content_id.encode('utf-8')` for author + blessings
  - Body referencing: `body_sha256` field in metadata pointing to separately-stored content
  - Serialization: YAML (canonical) or JSON
  - Trust tier derivation: peer-shared (unsigned/1-of-N) vs class-blessed (≥threshold)
  - Validity window semantics
  - Versioning policy: semver, minor additions backward-compat, major breaks require explicit opt-in
- [ ] `kaf-examples.md` — 3 annotated examples (routine, claude_md, skill_ref)
- [ ] `kaf-implementers-guide.md` — for someone building a KAF writer/reader in Go/Rust/TypeScript:
  - Canonical JSON algorithm (key sort, UTF-8 no escape, no whitespace)
  - SHA-256 of canonical bytes
  - Ed25519 sign over content_id as UTF-8 bytes
  - Reference test vectors (5 known-input/known-output cases)
- [ ] Commit: `docs(kaf): KAF 0.1 spec, examples, implementers guide`

---

## Task 2: Static spec site (kindredformat.org)

**Files:** `kindredformat/package.json`, `kindredformat/next.config.mjs`, `kindredformat/src/app/**`

- [ ] Minimal Next.js static export: renders the 3 markdown files, deploy-ready
- [ ] Use `next-mdx-remote` for markdown → HTML
- [ ] Clean typography (serif body, monospace code blocks)
- [ ] TOC sidebar for spec page
- [ ] Commit: `feat(kindredformat): static spec site scaffold`

---

## Task 3: 5 flagship seed grimoires content

**Files:** `docs/seed-grimoires/*/`

- [ ] Each grimoire has:
  - `README.md` — what this grimoire is for, who benefits, minimum member count
  - 3-5 artifacts in the appropriate format (markdown for claude_md/routine, JSON for skill_ref)
- [ ] **claude-code-patterns** — Claude Code usage patterns:
  - `claude_md.md` — CLAUDE.md snippet: TDD, frequent commits, explicit task boundaries
  - `routine-tdd-per-task.md` — step-by-step TDD with test-first failing proof
  - `routine-git-commits-per-task.md` — commit message conventions
  - `skill-ref-superpowers.json` — reference to superpowers plugin
- [ ] **postgres-ops** — production Postgres routines:
  - `routine-handle-bloat.md` — detect + fix via pg_stat_user_tables + VACUUM
  - `routine-migration-structure.md` — one migration per change, reversible, test upgrade+downgrade
  - `routine-backup-restore.md` — pg_dump strategy + PITR
- [ ] **llm-eval-playbook** — agent evaluation:
  - `routine-benchmark-harness.md` — how to structure task-agent benchmarks
  - `routine-cost-tracking.md` — per-request cost attribution
- [ ] **agent-security** — injection defenses + sandboxing:
  - `routine-injection-defense.md` — Kindred's own sanitizer patterns
  - `routine-sandboxing.md` — running untrusted agent output
- [ ] **kindred-patterns** — meta: patterns from building Kindred:
  - `claude_md.md` — behavioral guidelines used by this project (Think Before Coding, Simplicity, Surgical Changes, Goal-Driven Execution)
  - `routine-backend-tdd-style.md` — the TDD pattern used across all plans
- [ ] Commit: `docs(seed-grimoires): 5 flagship grimoires with initial artifacts`

---

## Task 4: Seed script (populate running backend)

**Files:** `scripts/seed_grimoires.sh`, `scripts/seed_grimoires.py`

- [ ] `seed_grimoires.py` — Python script that:
  1. Reads `KINDRED_BACKEND_URL` env var
  2. Generates a founder keypair (or loads from `~/.kin/seed.key`)
  3. Registers founder user + agent
  4. Creates 5 kindreds (slugs: claude-code-patterns, postgres-ops, llm-eval-playbook, agent-security, kindred-patterns)
  5. Joins founder's agent to each
  6. Reads artifact files from `docs/seed-grimoires/<slug>/`, uploads each as appropriate type
  7. Self-blesses where threshold=1
- [ ] Uses `kindred_client` (from `cli/` package) for HTTP + crypto
- [ ] Commit: `feat(scripts): seed_grimoires — populates backend with 5 flagship kindreds`

---

## Task 5: Onboarding benchmark

**Files:** `scripts/onboarding_benchmark.sh`, `.github/workflows/launch-benchmark.yml`

- [ ] `onboarding_benchmark.sh`:
  1. Start backend via docker-compose
  2. Create a founder + a kindred + an invite
  3. Start timer
  4. Run `pip install kindred-client` (from local path for dev, from PyPI in CI) + `kin join <url>`
  5. Run `kin ask <kindred> "test query"`
  6. Stop timer
  7. Print elapsed; exit 1 if >60s
- [ ] GitHub Actions workflow runs weekly + on-push to track regressions
- [ ] Commit: `feat(scripts): onboarding <60s benchmark + CI workflow`

---

## Task 6: Docs — Quick Start, Threat Model, Transparency

**Files:** `docs/quick-start.md`, `docs/threat-model.md`, `docs/transparency.md`

- [ ] `quick-start.md` (<1 page):
  - 3 commands to get going (install CLI, join kindred, first ask)
  - Pointer to plugin install for Claude Code users
  - Link to seed grimoires as templates
- [ ] `threat-model.md`:
  - Copy + expand §8 from spec
  - Per-mitigation pointer to code path
  - Known residual risks (C1 seq race, server-side keys in web UI v0, etc.)
- [ ] `transparency.md`:
  - Adversarial injection corpus block rate (auto-updated by CI: `100% on 50 payloads as of <date>`)
  - Open-source the corpus link: `backend/tests/adversarial/injection_corpus.json`
  - SBOM summary (optional)
- [ ] Commit: `docs(launch): quick start + threat model + transparency`

---

## Task 7: Top-level project README

**Files:** `README.md` (root)

- [ ] Root README acts as project landing:
  - What is Kindred (one-liner + tagline)
  - Repo layout (backend/, cli/, claude-code-plugin/, web/, kindredformat/, docs/)
  - Quick start pointer
  - Spec pointer
  - Plans overview (links to each plan)
  - Contribution guide (mini)
  - License
- [ ] Commit: `docs: top-level project README`

---

## Task 8: Final integration smoke test

**Files:** `scripts/integration_smoke.sh`

- [ ] Shell script (manual, not CI):
  1. `docker compose up -d` for backend
  2. Alembic upgrade head
  3. Run seed script → verify 5 kindreds created
  4. `kin join <invite>` → verify success
  5. `kin ask claude-code-patterns "tdd"` → verify artifact returned
  6. `kin save this` placeholder check
  7. Tear down
- [ ] Document in `README.md`
- [ ] Commit: `feat(scripts): end-to-end integration smoke test`

---

## Task 9: Launch checklist markdown

**Files:** `docs/launch/checklist.md`

- [ ] Mirror spec §16 launch checklist:
  - Pre-launch checks (seed grimoires, CI benchmark, injection block rate, landing pages)
  - Launch day (HN post, invite-only 200 tokens, digest start)
  - Post-launch (metric review, go/pivot/kill decision at T+30d)
- [ ] Commit: `docs(launch): checklist + metrics playbook`

---

## Success criteria

- KAF 0.1 spec publishable at `kindredformat.org` (static site, deploys clean)
- 5 seed grimoires with 3+ artifacts each, importable via seed script
- Onboarding benchmark green in CI (<60s)
- Transparency page shows 100% injection block rate
- Top-level README + quick-start make project navigable
- Integration smoke test reproducible on clean checkout

---

## Concerns / deferred

- Actual `kindredformat.org` DNS/hosting setup — ops task, not code
- PyPI publish of `kindred-client` — release engineering, post-launch
- Real OAuth-registered apps (GitHub App, Google) — ops, post-launch
- HN/launch copy polishing — marketing, post-this-plan
- Webhooks for GitHub repo references — v1
