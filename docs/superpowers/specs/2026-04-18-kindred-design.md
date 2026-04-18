# Kindred v0 — Design Spec

**Date:** 2026-04-18
**Status:** Draft for review (v2, post A-team critique)
**Pitch (one line):** *Your agent now knows what your kindred knows.*
**Tagline:** *Kindred — a knowledge co-op for you and your friends' AI agents.*

---

## 0. TL;DR

Kindred este o **infrastructură de commons pentru cunoaștere tacită între agenți AI**, organizată ca **co-op privat** între prieteni/colegi care folosesc agenți (Claude Code, Cursor, ChatGPT, custom). Fiecare grup (*a kindred*) deține un **grimoire**: o colecție de artefacte (CLAUDE.md-uri, routines, skills, refs) semnate, versionate, content-addressed, servite deterministic de un facilitator către agenții membri prin retrieval verificat.

**Nu este:** școală, MOOC, StackOverflow, Skool-clone, agent marketplace, feed public.
**Este:** supply chain verificată pentru context tacit, cu trust-scoped rooms și outcome-measurable transmission.

---

## 1. Principii fundamentale

Scrise aici ca să prevenim drift-ul în implementare. Orice decizie care încalcă unul din principii trebuie revizuită explicit.

### P1 — Agenții nu sunt elevi
Presupozițiile școlii (scarcity de profesor, secvențiere, examen-proxy, sezoane) nu se aplică agenților. Agenții sunt clonabili, nu uită, sunt verificabili, fără identitate stabilă, pot merge/split cunoaștere. Metafora corectă e **supply chain**, nu **pedagogie**.

### P2 — Provenance > Reputation
Fiecare bucată de knowledge servită are lanț vizibil: cine a semnat, când a fost vetted, ce benchmark a trecut, ce outcome-uri a produs. Reputation (ca pe SO) e ieftină și manipulabilă; provenance criptografic e scump de fake.

### P3 — Knowledge ca cod, nu proză
Artefactele sunt tipizate, content-addressed, verificabile, composable, opțional cu test harness atașat. Nu povești, nu humor pedagogic. Token-efficient, agent-native.

### P4 — Trust bounded & invizibil
Toate garanțiile criptografice rulează sub capotă. Userul nu vede chei, nu face "signing". Vede "verified ✓" și contribuie cu un click. Crypto e engine, nu UX.

### P5 — Contribution passivă, nu ops
Grimoire-ul moare dacă contribution e un task conștient. Side-effect al folosirii normale: auto-hook detectează "asta a mers", propune artifact, peer auto-approves la threshold. *Don't make me do knowledge ops.*

### P6 — Time-pinned, nu etern
Fiecare artefact are `valid_from` / `valid_until`. Knowledge stale expires din retrieval până la re-bless. Unlike wiki-urile care cresc toxic cu vârsta.

### P7 — Outcome-measurable
Fiecare `ask` lasă un audit trail; outcome-ul (succes, override, fail) se propagă înapoi ca semnal pe artefact. Spre deosebire de educația umană, transmisia e măsurabilă.

### P8 — Facilitator ≠ teacher
Facilitator-ul e cod determinist: policy engine + RAG librarian. Nu generează, nu predă. Elimină gâtuitura expertizei rare. Logica "scarcity de profesor" nu se aplică.

### P9 — Link is the install
Un URL care conține identitatea kindred-ului + invite-ul + bootstrap skill-ul. Click → onboarded <60s. Zero cont de tip user/parolă, zero config post-install. Discord ca gold standard de UX.

### P10 — Co-op economics
Member-owned, self-hostable, $0 până la X membri, apoi split cost infra. Zero creator-take-rate. Zero gamification-of-humans. "Gamification" doar pe outcome-uri obiective de agent (benchmark scores).

### P11 — Cross-vendor by design
Identitatea agentului e keypair, nu provider. Funcționează cu Claude Code, Cursor, ChatGPT, custom, cross-OS, cross-harness. Neutralitatea e moat-ul.

### P12 — Narrow wedge, protocol play
v0 target = **dev seniori care folosesc Claude Code / Cursor zilnic, în grupuri de 5-20 prieteni cross-org**. KAF (Kindred Artifact Format) e **open spec**; hosted kindred.sh e proprietary. Expansion post-PMF.

---

## 2. Ce *nu* este Kindred

Ca antidot la drift-ul conceptual:

| Nu este | Pentru că |
|---|---|
| O școală | Agenții nu sunt elevi (P1) |
| StackOverflow pentru agenți | SO = public + reputation; Kindred = private + provenance |
| Skool-clone pentru AI | Skool = creator-economy parasocial; Kindred = co-op member-owned |
| Curs / MOOC | Zero secvențiere, zero curriculum, zero credentialing |
| Agent marketplace | Nu vinzi skills, construiești commons private |
| Feed public de agenți (ca MoltBook) | Privat intenționat; viralitate prin capability envy, nu spectacol |
| Notion + Cursor rules done remote | Agent-native format, provenance, cross-vendor, outcome telemetry |

**Analogi umani acceptați:** mastermind privat, retreat de founderi recurring, co-op / credit union, heist crew cu grimoire partajat, salonul Royal Society 1660 înainte de instituționalizare. Toate: mici, trust-gated, peer, bounded, recurring, shared pool, zero ierarhie.

---

## 3. Actori & Vocabular

| Termen tehnic | Termen user-facing | Definiție |
|---|---|---|
| Human owner | *You* | Persoană care posedă unul+ agenți; autoritate finală pe scope și membership |
| Agent member | *Your agent* | Entitate cu keypair Ed25519; aparține unui owner; membră într-un kindred |
| Kindred | *Your kindred* / *a kindred* | Camera privată; grup cu membership verificat, grimoire propriu, facilitator dedicat |
| Co-op member | *Member* | Human care participă la un kindred (prin agentul său); toți sunt egali (no curator/member split pentru v0) |
| Grimoire | *Grimoire* | Corpusul de artefacte al unui kindred |
| Artifact | *Pattern* / *Entry* | Unitatea de knowledge (CLAUDE.md, routine, skill_ref, etc) |
| Facilitator | (invizibil) | Proces per-kindred: policy engine + RAG librarian |
| Blessing | *Approval* | Semnătură secundară (other member signs) promovând peer-shared → class-blessed |
| Provenance chip | *Trust badge* | Metadata afișat la retrieve: autor, vetting, tier, outcome history |

**Decizie v0:** curator dispare; toți membrii unui kindred sunt egali. Blessing = threshold N-of-M (default 2-of-total), nu rol dedicat.

---

## 4. Arhitectură (4 componente)

### 4.1 Identity & Trust Layer
- Keypair Ed25519 per agent, generat local la `kin join` și stocat în `~/.kin/` (permissions 0600).
- Owner auth = OAuth (GitHub/Google) sau passkey → server leagă `owner_id` la cheia publică a agentului.
- Atestare owner→agent: `sign(owner_sk, {agent_pubkey, scope, expiry})`. Scope = lista de kindreds + acțiuni permise (read/contribute).
- Cross-device: passkey-based recovery; keypair-urile pot fi re-derivate deterministic din secret phrase.
- Cross-vendor: provider-ul agentului (Anthropic/OpenAI/local) e irelevant; identity = keypair.

### 4.2 Grimoire (per kindred)

**Artefacte tipizate (v0 livrează primele 3):**

| Tip | Conținut | Format |
|---|---|---|
| `claude_md` | Instrucțiuni sistem de tip CLAUDE.md | markdown |
| `routine` | Procedură step-by-step cu pași numerotați | markdown + optional `test.sh` |
| `skill_ref` | Referință la un skill (Anthropic Skill, custom) | JSON `{name, version, hash, source_url}` |
| `repo_ref` *(v1)* | Link la repo + summary vetted extras | JSON; **no auto-clone/exec** |
| `conversation_distilled` *(v1)* | Q&A distillation | markdown + metadata |
| `benchmark_ref` *(v1)* | Test harness pentru a valida artefact downstream | JSON + script atașat |

**Proprietăți obligatorii per artefact:**
- `id` = SHA-256(canonical_content)
- `author_sig` = Ed25519 signature de la autor
- `blessed_sigs` = listă de semnături peer (0+)
- `tier` derivat: `class-blessed` dacă ≥ threshold, altfel `peer-shared`
- `valid_from`, `valid_until` (default: from=now, until=now+6 luni; configurabil)
- `outcome_stats` = agregat: N utilizări, success rate, last used

**Imutabilitate:** update = artefact nou cu id nou. Grimoire-ul are un "active pointer" per logical-name → id; schimbarea pointerului e un eveniment auditabil.

### 4.3 Facilitator (per kindred)

**Policy engine (determinist, zero LLM pe calea critică):**
- Enforce trust tiers la retrieve: `peer-shared` nu se injectează fără `accept_peer_shared=true` în cerere.
- Sanitizare inter-agent: fiecare artefact servit e delimitat `<kin:artifact id=... tier=...>...</kin:artifact>`; patterns de injection cunoscute sunt escape-uite; output-uri externe din `repo_ref` sunt summary-vetted, niciodată raw pass-through.
- Validity window check: artefactele expired nu apar în retrieve; returnate marked `expired` doar explicit.
- Rate limit per `agent_pubkey`: default 30 ask/min, 10 contribute/h; configurabil.
- Audit log append-only, signed de facilitator key; fiecare entry: {ts, agent, action, artifact_ids_returned, outcome (when reported back)}.

**Librarian (RAG peste corpus):**
- Embedding-uri la ingest (pgvector).
- La `ask`: top-k retrieve (k=5 default), filtered by tier + validity.
- Returnează artefactele literal + provenance chips. **Zero generare LLM nouă.** Agentul apelant decide cum le folosește.

**Outcome telemetry:**
- Endpoint `report_outcome(audit_id, result, notes)`. Result ∈ {success, partial, fail, overridden}.
- Agregat pe artefact → `outcome_stats`. Afectează ordering la retrieve (nu hard-filter, dar signal).

**Match-making (v1):** identifică alt agent-membru care a întrebat/rezolvat recent; oferă contact pull-based cu consimțământ reciproc al owner-ilor.

### 4.4 Client SDK + Harness Integrations

**CLI `kin` (v0 core):**
- `kin join <invite_url>` — keypair, atestare, config local
- `kin ask <kindred> "<question>"`
- `kin contribute <kindred> --type routine --file path.md`
- `kin save this` — captures last AI conversation outcome, proposes artifact
- `kin status` — active kindreds, recent activity, member count
- `kin leave <kindred>` — revocă local, notifică server

**Harness integrations livrate în v0:**
- **Claude Code plugin** — skill care trigger pe pattern-uri de întrebare + MCP server care expune grimoire-ul + hook PostToolUse pentru outcome telemetry.
- **Cursor integration** — MCP server config injectat în `~/.cursor/mcp.json` + `.cursorrules` fragment.
- **Generic HTTP API** — pentru agenți custom sau alte harness-uri.

**v0.5:** ChatGPT Custom GPT (Action cu OAuth + preconfigured instructions).

---

## 5. KAF — Kindred Artifact Format (open spec)

Documentat separat la `kindredformat.org` (public), versionat semantic.

**Exemplu canonical:**
```yaml
kaf_version: "0.1"
type: routine
id: sha256:abc123...
author: ed25519:9f2a...
author_sig: ed25519:7b3c...
blessed_sigs:
  - {signer: ed25519:1a2b..., ts: 2026-04-18T10:00:00Z, sig: ed25519:...}
valid_from: 2026-04-18T00:00:00Z
valid_until: 2026-10-18T00:00:00Z
tags: [postgres, performance]
logical_name: "handle-table-bloat"
outcome_stats:
  uses: 23
  success_rate: 0.91
content: |
  # Handle Postgres Table Bloat
  1. Identify bloat: `SELECT ...`
  2. ...
test_harness:  # optional
  script: ./test.sh
  last_pass: 2026-04-17T12:00:00Z
```

**Deschis:** alții pot implementa reader/writer compatibili. Tu controlezi hosted execution.

---

## 6. Onboarding Protocol (link is the install)

### Format link
```
https://kindred.sh/k/<slug>?inv=<token>
```
- Slug lizibil, share-able (`heist-crew`, `postgres-team`).
- Token: one-time-use, TTL 7 zile default, revocable, capacity-limited.
- Deep-link: `kindred://join?k=<slug>&inv=<token>` pentru app handlers.

### Fluxuri

**A) Nu are client:**
1. Browser → landing kindred (nume, #membri, public description).
2. Butoane: *Install for Claude Code / Cursor / ChatGPT / CLI*.
3. Click → one-liner în clipboard: `curl -sSL kindred.sh/install | sh -s -- join <token>`.
4. Instalator: OAuth (GitHub/Google sau passkey) → keypair local → atestare → accept invite → harness-specific plugin install.
5. Agentul e gata. <60s end-to-end (benchmark CI-enforced).

**B) Are client:**
1. Click → deep-link → pop-up local "Join heist-crew?".
2. Confirm → <5s.

**C) Dev custom:**
1. Click → snippet `pip install kindred-client && kin join <token>`.

### Invariante UX (CI-enforced)
- Zero username/parolă (OAuth sau passkey only).
- Zero config post-install.
- Un-install = `kin leave <kindred>` (un buton în UI).
- Cross-device: login pe device nou → passkey → kindreds reapar.

### Contribution passivity (P5 în practică)
- **Auto-hook "worked" signals** în Claude Code plugin: test pass + zero override uman 30min → "Propose this routine to heist-crew? [Y/n]".
- **`kin save this`** one-liner.
- **1-tap approve** via push/email când altcineva propune.
- **Threshold auto-bless**: 2-of-N semnături → class-blessed automat.

---

## 7. Data Flow (golden path)

1. Alice creează `#heist-crew` pe kindred.sh, primește invite link.
2. Alice trimite link pe Signal la Bob, Carol, Dan, Eve.
3. Bob click → Install for Claude Code → 47s later, agentul lui Bob e membru.
4. Alice dă `kin contribute --type claude_md --file ~/code/projX/CLAUDE.md`. Artefact semnat de Alice, intră ca `peer-shared` (1-of-5, sub threshold 2).
5. Carol vede propunerea în `kin status`, aprobă cu un click. Devine `class-blessed` (2-of-5).
6. Bob lucrează în Claude Code, întreabă "how do we structure migrations?". Plugin-ul invocă `kin ask #heist-crew "migration structure"`. Facilitator retrieve 2 artefacte blessed, le injectează în context cu provenance chips.
7. Bob aplică soluția, test pass, zero override. Hook raportează `report_outcome(audit_id, "success")`. Artefactele primesc +1 success.
8. Săptămâna următoare, digest email: "heist-crew: 12 asks, 3 new patterns, 2 artifacts expired".

---

## 8. Threat Model & Mitigări

| Amenințare | Mitigare |
|---|---|
| Poisoned artifact uploadat | Signing + blessing threshold + tier visibility + peer-shared quarantine |
| Sybil / impersonation | Keypair + OAuth owner atestation + invite token one-time |
| Facilitator jailbreak | Policy engine determinist, LLM-free pe calea critică |
| Cross-kindred leak | Context izolat per kindred; cross-post = acțiune umană explicită |
| Supply-chain pe skill_ref | Hash-pinned; update = artifact nou, opt-in |
| Ranking gaming | v0 = retrieval bazat pe similarity + outcome, nu popularity; v1 = anti-gaming |
| Distillation poisoning | Distilled intră peer-shared, needs blessing ca să fie servit default |
| Tool-output injection | Output-uri externe summary-ate la vet-time, nu raw |
| Consent confusion | Scope explicit în atestare owner→agent; owner poate revoke |
| Bad bless propagation | Timeline + rollback: revert kindred la snapshot anterior |
| Prompt injection pe ask | Input sanitization + delimitere clară în serving format |
| Data exfiltration via agent | Rate limits + audit log + owner-visible activity feed |

**Transparency page:** open-sources injection corpus + metrics de blocking rate. Trust via openness.

**Rollback:** fiecare kindred are event log. `kin rollback <kindred> --to <timestamp>` revine la snapshot. Acțiune privilegiată (cere threshold approval).

---

## 9. MVP Scope (v0)

### In
- Identity: Ed25519 keypair, OAuth owner attestation, passkey recovery.
- Kindred CRUD: create, invite (link), join, leave, list members.
- Artefacte: `claude_md`, `routine`, `skill_ref` — signing, threshold blessing, content-addressed storage, validity window.
- Facilitator: policy engine + RAG librarian (pgvector); no LLM generation.
- Trust tiers: `class-blessed`, `peer-shared`.
- CLI `kin` complet (Python, pip-installable).
- Claude Code plugin (skill + MCP + hook).
- Cursor integration (MCP + cursorrules).
- Web UI minimal: landing/invite, kindred view, propose/approve, audit log, rollback.
- Onboarding <60s benchmark în CI.
- Adversarial injection test suite (50+ payloads) în CI.
- Outcome telemetry endpoint + aggregation.
- KAF 0.1 spec publicat la kindredformat.org.

### Out (v1+)
- `repo_ref`, `conversation_distilled`, `benchmark_ref`.
- Match-making inter-agent.
- ChatGPT Custom GPT integration (v0.5).
- Fine-tuning pipeline pe (state, action, outcome) triplets.
- Public kindred directory / leaderboards (pariul B).
- Vanilla skill cyber-vetting pipeline (pariul A).
- Monetizare / billing.
- Federation cross-server.
- Research paper publication.

---

## 10. Tech Stack

- **Backend:** Python 3.12 + FastAPI. Async, typed.
- **Storage:** Postgres 16 (metadata, membership, audit log, event stream), object store content-addressed (MinIO dev, S3 prod).
- **Vector:** pgvector pe artefacte.
- **Crypto:** `pynacl` (libsodium).
- **Embeddings:** provider-abstract; default `text-embedding-3-small`, swap-able la local `bge-small` pentru self-host.
- **CLI:** Python + Typer.
- **Claude Code plugin:** distributed as plugin package; MCP server in Python.
- **Cursor:** MCP server same codebase, config snippets generated.
- **Frontend:** Next.js 15 App Router, Tailwind, shadcn/ui.
- **Auth:** Auth.js (OAuth GitHub/Google) + WebAuthn pentru passkey.
- **Deploy v0:** docker-compose single-tenant self-host + kindred.sh hosted (fly.io / Railway).
- **CI:** GitHub Actions; onboarding benchmark + injection suite enforced.

---

## 11. Success Criteria & North-Star Metric

### North-star metric
**Active Kindreds** = kindreds cu ≥3 members + ≥5 asks/săptămână + ≥1 new contribution/săptămână, măsurat la 30+ zile de la creare.

Target post-launch:
- T+30d: 5 active kindreds (seed-uite + 0-2 organic).
- T+90d: 20 active kindreds.
- T+180d: 100 active kindreds + viral coefficient >1.

### Secondary metrics
- **Onboarding time p50** <60s (CI test) și p50 real <120s.
- **Viral coefficient** per invite link — tracked ziua 1.
- **Ask → success rate** — % din `ask` care primesc `report_outcome=success`.
- **Contribution per member per week** — obiectiv ≥0.5 (adică >jumătate din membri contribuie săptămânal).
- **Injection block rate** — 100% pe test corpus (CI gate).

### MVP success criteria (hard gates)
1. 3 kindreds externe (non-fondator) E2E cu agenți reali — Claude Code + Cursor, minim 2 provideri AI diferiți.
2. Signing + blessing + verification runtime-verified cu chei reale; tampering detectat 100% la verify.
3. Adversarial injection suite: 100% blocked/quarantined pe ≥50 payloads.
4. Latență `ask` <2s p50, <5s p99 pe corpus de 100 artefacte.
5. Onboarding CI test <60s click-to-first-query.
6. Demo reproducible: agent de dev primește răspuns provenance-verified dintr-un kindred curated.

---

## 12. Virality & Growth Loops

### Primary loop (capability envy)
1. Member ridică agentul prin kindred.
2. Outcome vizibil (viteză, calitate) impresionează prieteni externi.
3. Prieten cere invite; member dă link.
4. Prieten joins; ciclu se închide și crește.

Condiție critică: **viral coefficient >1 la 30 zile** → refactor produs dacă nu.

### Secondary loops
- **Kindred forking**: un membru crează un kindred nou din structura altuia (artefacte publice read-only seed); invită prieteni → crească #kindreds.
- **Cross-kindred members**: users cu 2+ kindreds amplifică discovery inter-grup.
- **Digest email săptămânal**: menține engagement + prompts de contribuție.

### Launch: 5 flagship seed kindreds (cold-start kill)
Construite de fondator + prieteni, public preview read-only structure, invite-only write:
1. **Claude Code Patterns** — cum folosesc devii seniori Claude Code zilnic.
2. **Postgres Ops** — routine, troubleshooting, migrations.
3. **Cursor Rules Garden** — .cursorrules care chiar merg.
4. **LLM Eval Playbook** — cum evaluezi rezultate de agent în producție.
5. **Agent Security** — injection defenses, sandboxing patterns.

Fiecare: 10-20 artefacte blessed, 3-5 membri activi, digest public "what changed this week".

### Anti-viral guards
- Zero public shaming / drama surface — privatitate by default.
- Zero gamification de oameni (nu levels, nu XP, nu streaks).
- Zero creator-take-rate — co-op pur.

---

## 13. Compounding Memory (v1+ vision, v0 data model readiness)

Chiar dacă v0 nu face fine-tuning, data model-ul îl pregătește:

- **Triplet logging**: fiecare `ask` + artefactele returnate + `outcome` formează un (state, action, outcome) triplet stocat în event stream.
- **Kindred-as-corpus**: în v1, triplets + artefactele blessed devin corpus de fine-tune opt-in pentru un **agent-per-kindred** custom.
- **Ablation framework**: benchmarks standardizate care compară agent+kindred vs agent solo, per task-type. Demonstrabil → research paper.

v0 nu implementează fine-tune pipeline-ul, dar log-ul și schema sunt compatibile.

---

## 14. Risks & Tradeoffs (honest)

| Risc | Likelihood | Impact | Mitigare |
|---|---|---|---|
| Grimoire rot după 6 luni | High | High | Validity windows + digest + contribution passivity |
| Signing UX prea complex | Medium | High | Invizibilitate totală; "verified ✓" not "Ed25519" |
| Viral coefficient <1 | Medium | Critical | Track de ziua 1; refactor produs dacă persistă |
| Anthropic/OpenAI copy feature-ul | Medium | Medium | Moat = cross-vendor neutrality + open protocol |
| Cold-start (nimeni n-are cu cine forma grup) | High | High | 5 flagship seed kindreds la launch |
| Enterprise vrea on-prem → ripează hosted moat | Low (v0) | Medium | Self-host explicit acceptat; hosted = convenience |
| Legal (IP ownership pe artefacte) | Medium | Medium | v0 = autor = owner; ToS clar; v1 clarifică colectiv |
| Onboarding >60s pe Windows / edge cases | Medium | Medium | CI test pe toate OS; fallback instrucțiuni manuale |
| Performance la 1000+ artefacte | Low (v0 scale) | Low | pgvector scales; v1 sharding per kindred |
| Narrow wedge pierde non-dev audiences | Certain | Low (accepted) | Wedge ruthless; expansion post-PMF |

**Tradeoffs acceptate:**
- Privacy-first pierde top-funnel vizibilitate (nu ne viralizăm pe X cu screenshots). Acceptăm — loop-ul e capability envy, nu spectacol.
- Co-op economics → revenue lent. Hosted tier gratuit până la X; plata apare post-scale sau enterprise.
- Narrow wedge (dev Claude Code/Cursor) → pierdem researchers/creatives/non-tech early. Asumat, expansion după PMF.

---

## 15. Unknowns rezolvate în v1+

1. **Cross-vendor identity la scară** — v0 self-issued keypair; v1 atestare federată (DID sau similar).
2. **IP ownership al distilled conversations** — v0: autor=agent care contribuie; v1: drepturi colective explicite.
3. **Anti-self-host moat economic** — v0 acceptă self-host; moat se construiește prin vetting pipeline (pariul A) + directory public (pariul B) post-PMF.
4. **Fine-tune pipeline** — v1 folosind triplet logs.
5. **Federation cross-server** — dacă kindredformat.org devine standard, servere multiple pot federa kindreds.

---

## 16. Launch Checklist

### Pre-launch (înainte de T-0)
- [ ] 5 seed kindreds cu ≥10 artefacte fiecare, blessed
- [ ] Onboarding CI test verde <60s pe macOS + Linux + WSL
- [ ] Injection suite 100% block rate
- [ ] Landing page kindred.sh + kindredformat.org pentru KAF
- [ ] Claude Code plugin publicat
- [ ] Cursor integration testată
- [ ] Docs: Quick Start (sub 1 pagină), Threat Model, KAF Spec

### Launch
- [ ] HN post: "Show HN: Kindred — a knowledge co-op for you and your dev friends' AI agents"
- [ ] Invite-only la început (200 tokens) → urmărim viral coefficient
- [ ] Digest săptămânal start ziua 8

### Post-launch (T+30d)
- [ ] Retro cu toți membrii seed
- [ ] Metric review vs north-star
- [ ] Decision gate: continue / pivot / kill

---

## 17. Glossary

- **Kindred** — camera privată; grup co-op cu grimoire propriu.
- **Grimoire** — corpusul de artefacte al unui kindred.
- **Artifact / Pattern** — unitate de knowledge, signed, content-addressed.
- **KAF** — Kindred Artifact Format, open spec la kindredformat.org.
- **Facilitator** — proces per-kindred (policy + RAG), nu persoană.
- **Blessing** — semnătură secundară care promovează peer-shared → class-blessed.
- **Provenance chip** — metadata trust afișat la retrieve.
- **Trust tier** — `class-blessed` | `peer-shared` | (v1) `vanilla-vetted`.
- **Validity window** — `valid_from` / `valid_until` pe artefact.
- **Outcome telemetry** — (success/partial/fail/overridden) raportat post-ask.
- **Viral coefficient** — invites per member, tracked de ziua 1.
- **Capability envy** — primary viral loop: "my agent got better, yours hasn't".
