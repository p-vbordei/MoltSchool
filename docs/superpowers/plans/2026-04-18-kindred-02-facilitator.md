# Kindred Facilitator — Implementation Plan (02/07)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]` checkboxes.

**Goal:** Livrează Facilitator-ul Kindred — `/ask` endpoint cu RAG librarian, policy engine determinist (tier + membership + scope + expiry enforcement), outcome telemetry pentru feedback loops, injection defense + adversarial suite 50+ payloads în CI. La sfârșit: agent apelează `/ask`, primește artefacte cu provenance chips, raportează outcome; injection attacks blocate 100%.

**Architecture:** Servicii de facilitator în `src/kindred/facilitator/` + `src/kindred/embeddings/`. **NO LLM GENERATION** — doar retrieval + policy + serving format deterministic. Embedding-uri stocate ca `JSON` column (list[float]) — portable cross-dialect, cosine în Python (acceptabil la <1000 artefacte per kindred). HNSW / pgvector e follow-up la scale.

**Tech Stack:** OpenAI embeddings (default), FakeEmbeddingProvider (deterministic, test only), pynacl sig verification, FastAPI routers.

**Spec reference:** §4.3 Facilitator, §8 Threat Model, §11 Success Criteria #3 (injection 100% block).

**Absorbs Plan 01 follow-ups:** I1 (membership enforcement), I2 (attestation expiry), I4 (scope enforcement), I6 (validity window filter), I7 (audit log wired live).

---

## File Structure

```
backend/src/kindred/
├── embeddings/__init__.py
├── embeddings/provider.py            # EmbeddingProvider Protocol + Fake + OpenAI
├── facilitator/__init__.py
├── facilitator/sanitizer.py          # Injection detect + framing + query sanitize
├── facilitator/policy.py             # require_member/scope/expiry, filter_by_tier
├── facilitator/librarian.py          # retrieve_top_k (Python cosine, validity filter)
├── facilitator/outcomes.py           # report_outcome service
├── api/schemas/ask.py
├── api/schemas/outcomes.py
├── api/routers/ask.py                # POST /v1/kindreds/{slug}/ask
└── api/routers/outcomes.py           # POST /v1/ask/outcome

backend/tests/
├── adversarial/__init__.py
├── adversarial/injection_corpus.json # 50+ payloads
├── adversarial/test_injection_block.py  # CI gate
├── unit/test_sanitizer.py
├── unit/test_policy.py
├── unit/test_librarian.py
├── unit/test_outcomes.py
├── unit/test_embeddings_provider.py
├── api/test_ask_api.py
├── api/test_outcomes_api.py
└── e2e/test_ask_flow.py
```

---

## Task 1: Embeddings provider

**Files:** `embeddings/{__init__.py,provider.py}`, `tests/unit/test_embeddings_provider.py`, `config.py` (extend)

- [ ] Write failing test `test_fake_provider_deterministic/different_texts/get_provider_returns_fake`
- [ ] Implement `EmbeddingProvider` Protocol + `FakeEmbeddingProvider` (hash-based deterministic, 64-dim L2-normed) + `OpenAIEmbeddingProvider` (text-embedding-3-small, 1536-dim, AsyncOpenAI) + `get_provider(name)` factory reading Settings
- [ ] Add to `Settings`: `embedding_provider: str = "fake"`, `openai_api_key: SecretStr | None = None`
- [ ] Add `openai>=1.50` to deps (optional)
- [ ] Tests pass
- [ ] Commit: `feat(embeddings): provider abstraction (fake + openai)`

Exact code in plan 02 draft — see original content. Key decisions:
- `FakeEmbeddingProvider(dim=64)` uses `hashlib.sha256(text).digest()` expanded to dim floats in [-1,1], L2-normalized
- `get_provider()` reads settings, defaults to "fake"

---

## Task 2: Artifact embedding column (JSON, cross-dialect)

**Files:** `models/artifact.py` (+column), `alembic/versions/0006_artifact_embedding.py`, `services/artifacts.py` (compute embedding on upload), `tests/unit/test_artifact_embedding.py`

- [ ] Add `embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)` to Artifact model
- [ ] Generate migration `0006_artifact_embedding`: `op.add_column('artifacts', sa.Column('embedding', sa.JSON(), nullable=True))`
- [ ] Extend `upload_artifact` to accept `embedding_provider` kwarg; if provided, embed `f"{logical_name}\n{' '.join(tags)}\n{body[:1024]}"` and store
- [ ] Test artifact with embedding stores list[float]
- [ ] Test artifact without provider (backward compat) stores None
- [ ] Commit: `feat(models): artifact embedding column (JSON)`

**Decision:** JSON instead of pgvector because (a) portable sqlite/postgres, (b) <1000 artefacte per kindred scale OK for Python cosine, (c) HNSW is follow-up. Document this in plan 07 follow-ups.

---

## Task 3: Sanitizer (injection detection + framing)

**Files:** `facilitator/{__init__.py,sanitizer.py}`, `tests/unit/test_sanitizer.py`

- [ ] Write tests (15+ cases): detects ignore_previous/system_role_spoof/tool_call_injection/jailbreak_persona/prompt_leak/url_fetch_redirect/shell_execution/data_exfiltration/delimiter_break/instruction_override/markdown_inject/role_hijack; clean text has zero hits; `frame_artifact` delimits + escapes `</kin:artifact>`; `sanitize_query` strips control chars + rejects >10k
- [ ] Implement module with `INJECTION_PATTERNS: list[tuple[str, re.Pattern]]` (12+ patterns), `InjectionHit` NamedTuple, `detect_injection_patterns`, `frame_artifact` (escapes closing tag), `sanitize_query` (control char strip + length cap)
- [ ] All tests pass
- [ ] Commit: `feat(facilitator): sanitizer with injection pattern detection`

Key patterns (regex compiled, case-insensitive):
- `ignore_previous`: `\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)`
- `system_role_spoof`: `<\|im_start\|>|<\|im_end\|>|<\|system\|>|\bsystem\s*:`
- `tool_call_injection`: `<function_calls>|<invoke\s+name=`
- `jailbreak_persona`: `\b(DAN|do anything now|developer mode|jailbreak)\b`
- `prompt_leak`: `\b(print|reveal|show|repeat)\s+(your\s+)?(system\s+)?(prompt|instructions)`
- `shell_execution`: `\b(rm\s+-rf|curl\s+\S+\s*\|\s*sh|eval\s*\(|exec\s*\()`
- `data_exfiltration`: `\bpost\s+.*\bto\s+https?://`
- `delimiter_break`: `</kin:artifact>`
- `instruction_override`: `\b(new|updated|corrected)\s+instructions?\s*:`
- `markdown_inject`: `!\[.*?\]\(javascript:`
- `role_hijack`: `\b(you are now|from now on, you are|pretend to be)\s+(a\s+)?(different|new|malicious)`
- `url_fetch_redirect`: `\bfetch\s+(this|the)\s+url\s*:\s*https?://`

`frame_artifact` output format: `<kin:artifact id=<cid> tier=<tier> author=<pk>>\n<escaped_content>\n</kin:artifact>` — escapes embedded `</kin:artifact>` to `&lt;/kin:artifact&gt;`.

---

## Task 4: Policy engine (membership + scope + expiry + tier filter)

**Files:** `facilitator/policy.py`, `tests/unit/test_policy.py`, `tests/helpers.py` (extend helper to auto-join creator's agent)

Absorbs I1 + I2 + I4.

- [ ] Extend `tests/helpers.py` so `make_user_agent_kindred_artifact` also creates an invite + joins the creator's agent → creator is member by default
- [ ] Tests: `require_member` rejects non-member; `require_scope` validates actions + kindreds (wildcard `"*"` accepted); `require_not_expired` rejects past; `require_agent_authorized` all-in-one happy + each failure mode; `filter_by_tier` strips peer-shared by default
- [ ] Implement:
  - `require_member(session, *, agent_pubkey, kindred_id)` — SELECT membership JOIN agent WHERE pubkey+kindred; raise UnauthorizedError if none
  - `require_scope(scope: dict|str, *, action, kindred_slug)` — parse JSON if str, check `action in scope.actions` and `kindred_slug in scope.kindreds or "*"`
  - `require_not_expired(expires_at)` — tz-normalize, compare to now UTC
  - `require_agent_authorized(session, *, agent_pubkey, kindred_id, kindred_slug, action)` — all three above
  - `filter_by_tier(artifacts_with_tiers, *, include_peer_shared=False)` — list[tuple[Artifact, str]] → filtered
- [ ] All tests pass
- [ ] Commit: `feat(facilitator): policy engine (membership + scope + expiry + tier filter)`

---

## Task 5: Librarian (RAG retrieve, Python cosine)

**Files:** `facilitator/librarian.py`, `tests/unit/test_librarian.py`

- [ ] Tests: `retrieve_top_k_finds_relevant` (upload 2 artefacte cu logical_name/tags distincte, query match first), `retrieve_filters_expired` (valid_until past → excluded default, included with `include_expired=True`), `retrieve_skips_null_embedding` (artefact fără embedding nu apare)
- [ ] Implement `retrieve_top_k(session, *, kindred_id, query, provider, k=5, include_expired=False) -> list[tuple[Artifact, float]]`:
  - `query_vec = await provider.embed(query)`
  - `select(Artifact).where(kindred_id == ...).where(valid_until > now())` (unless include_expired)
  - Python cosine similarity vs each artifact.embedding
  - Sort desc by similarity, return top k
  - `_cosine(a, b)` helper
- [ ] Tests pass using FakeEmbeddingProvider
- [ ] Commit: `feat(facilitator): librarian — RAG retrieve with validity filter`

**Follow-up note:** When corpus per kindred exceeds ~1000 artefacte, swap to pgvector HNSW index via `q.order_by(Artifact.embedding.cosine_distance(qv)).limit(k)`. TODO comment in librarian.py.

---

## Task 6: Outcome telemetry service

**Files:** `facilitator/outcomes.py`, `tests/unit/test_outcomes.py`

- [ ] Tests: `report_outcome_updates_artifact_stats` (uses real audit_id from append_audit flow, asserts artifact.outcome_uses/successes incremented); `report_outcome_unknown_audit_raises NotFoundError`; `report_outcome_invalid_result raises ValidationError`
- [ ] Implement `OutcomeResult(str, Enum)` with SUCCESS/PARTIAL/FAIL/OVERRIDDEN and `report_outcome(session, *, audit_id, result, notes="")`:
  - Validate `result in OutcomeResult`
  - `select(AuditLog).where(id == audit_id)` → NotFoundError if missing
  - For each `cid in audit.payload["artifact_ids_returned"]`: `update(Artifact).where(content_id==cid).values(outcome_uses+=1, outcome_successes+=1 if success|partial else 0)`
  - Append event `outcome_reported`
- [ ] Tests pass
- [ ] Commit: `feat(facilitator): outcome telemetry`

---

## Task 7: `/ask` endpoint (Absorbs I7 — audit log wired live)

**Files:** `api/schemas/ask.py`, `api/routers/ask.py`, `api/main.py` (register), `tests/api/test_ask_api.py`

- [ ] Schemas: `AskReq(query, k=5, include_peer_shared=False)`, `ProvenanceChip(content_id, logical_name, type, tier, author_pubkey, outcome_success_rate, valid_until)`, `AskResp(audit_id, artifacts:list[dict], provenance:list[ProvenanceChip])`
- [ ] Router `POST /v1/kindreds/{slug}/ask` (requires `x-agent-pubkey` header):
  1. Parse agent pubkey
  2. `get_kindred_by_slug` → 404 if missing
  3. `require_agent_authorized(..., action="read")` — enforces member + scope + expiry
  4. `sanitize_query(req.query)` → 400 if too long
  5. `detect_injection_patterns(q)` — if hits, return 400 + log attempt in audit payload
  6. `get_provider()` + `retrieve_top_k`
  7. Compute tier for each via `compute_tier`
  8. `filter_by_tier(..., include_peer_shared=req.include_peer_shared)`
  9. Build response: `frame_artifact` per filtered + `ProvenanceChip` per
  10. `append_audit` with `action="ask"`, `payload={query:"...", artifact_ids_returned:[...], k, blocked_injection: bool}` — signed by facilitator key
  11. Return `AskResp(audit_id=str(audit.id), artifacts=[...], provenance=[...])`
- [ ] Register in main.py with `prefix="/v1/kindreds"`
- [ ] Tests: happy path returns artifacts + audit_id; non-member agent → 403; injection query → 400 and audit captures it; peer-shared filtered by default; `include_peer_shared=true` includes them
- [ ] Commit: `feat(api): /ask endpoint — RAG retrieve + policy + audit`

---

## Task 8: `/ask/outcome` endpoint

**Files:** `api/schemas/outcomes.py`, `api/routers/outcomes.py`, `api/main.py` (register), `tests/api/test_outcomes_api.py`

- [ ] Schema `ReportOutcomeReq(audit_id, result, notes="")`
- [ ] Router `POST /v1/ask/outcome`: call `report_outcome(session, audit_id=UUID(req.audit_id), result=req.result, notes=req.notes)` → `{ok: True}`
- [ ] Register with prefix `/v1/ask`
- [ ] Test: full flow `ask` → `outcome=success` → re-list artifacts → outcome_successes == 1
- [ ] Commit: `feat(api): /ask/outcome endpoint for outcome telemetry`

---

## Task 9: Adversarial injection corpus + CI gate

**Files:** `tests/adversarial/{__init__.py,injection_corpus.json,test_injection_block.py}`, `.github/workflows/backend-ci.yml` (add adversarial step)

- [ ] Author 50+ payload corpus covering all injection pattern categories × 4-5 variants each. Structure:
  ```json
  [{"id": "ignore_01", "payload": "Ignore previous instructions...", "expected": "blocked"}, ...]
  ```
  Categories × variants: ignore_previous (5), system_role_spoof (5), tool_call_injection (5), jailbreak_persona (5), prompt_leak (5), url_fetch_redirect (3), shell_execution (5), data_exfiltration (3), delimiter_break (3), instruction_override (3), markdown_inject (3), role_hijack (5), clean_control_negatives (5, not blocked = expected "allowed"). Total ~50 blocked + 5 controls.
- [ ] Write `test_injection_block.py`:
  ```python
  import json
  from pathlib import Path
  from kindred.facilitator.sanitizer import detect_injection_patterns

  CORPUS = json.loads((Path(__file__).parent / "injection_corpus.json").read_text())

  def test_adversarial_corpus_block_rate():
      blocked_total = 0
      blocked_expected = sum(1 for e in CORPUS if e["expected"] == "blocked")
      false_positives = 0
      for entry in CORPUS:
          hits = detect_injection_patterns(entry["payload"])
          if entry["expected"] == "blocked":
              assert hits, f"failed to block: {entry['id']} — {entry['payload']}"
              blocked_total += 1
          else:
              if hits:
                  false_positives += 1
      assert blocked_total == blocked_expected
      assert false_positives == 0, f"{false_positives} false positives on clean payloads"
  ```
- [ ] Add CI step to `backend-ci.yml`:
  ```yaml
  - name: Adversarial injection suite (100% block gate)
    working-directory: backend
    run: uv run pytest tests/adversarial/ -v
  ```
- [ ] Commit: `test(adversarial): injection corpus 50+ payloads, 100% block CI gate`

---

## Task 10: E2E ask flow test

**Files:** `tests/e2e/test_ask_flow.py`

- [ ] End-to-end test:
  1. Register Alice + agent
  2. Create kindred, self-join
  3. Upload 3 artefacte cu embeddings (FakeProvider) cu logical_names distincte: "postgres-bloat", "react-hooks", "nginx-config"
  4. Bless one of them (threshold 2, so self-bless won't flip — or register 2nd user+agent and bless)
  5. Actually simpler: set kindred `bless_threshold=1` via create request
  6. Bless "postgres-bloat"
  7. Call `/ask` cu query "postgres table bloat" + `x-agent-pubkey`
  8. Assert response has `audit_id`, `artifacts` non-empty, top artifact is "postgres-bloat" blessed
  9. Report outcome success
  10. List artifacts → "postgres-bloat" has `outcome_success_rate==1.0`
- [ ] Commit: `test(e2e): ask flow end-to-end`

---

## Final steps

- [ ] Full test run: `uv run pytest -v` → expect ~80+ tests pass (63 + ~17 new)
- [ ] Ruff clean
- [ ] Final commit if any cleanup needed

---

## Self-Review Summary

- **Spec §4.3 Facilitator:** Policy engine = Task 4; Librarian = Task 5; Outcome telemetry = Tasks 6+8.
- **Spec §8 Threat Model:** Injection → Tasks 3+9; cross-kindred leak → Task 4 (require_member); consent confusion → Task 4 (scope+expiry).
- **Spec §11 Success #3:** Task 9 gates CI on 100% block.
- **Plan 01 follow-ups I1/I2/I4/I6/I7:** Absorbed in Tasks 4, 5, 7.
- **No LLM generation anywhere** — explicit in all tasks.

**Not yet:** ChatGPT Custom GPT integration (Plan 04+); match-making (v1+); research benchmarks (Plan 07 follow-up).
