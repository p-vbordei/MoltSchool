# Kindred Retrieval-Utility & Network-Health Implementation Plan (08/??)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Shift the measurement lens from "did we ship components" to "does retrieval change agent behavior for the better." Instrument every `/ask`, automate outcome capture from Claude Code, expose four first-principles indicators (retrieval utility, time-to-first-useful-retrieval, trust propagation latency, staleness cost) via a backend endpoint and a web health dashboard.

**Architecture:** Zero new tables. Extend `AuditLog.payload` (JSON) with rich retrieval metadata; compute indicators by aggregating existing `audit_log` + `events` + `blessings` + `artifacts` via a new `kindred.services.health` module; expose under `GET /v1/kindreds/{slug}/health`; render in a new `/dashboard/[slug]/health` page. Automate outcome reporting by extending the PostToolUse hook to call a new `kin report` CLI subcommand keyed by audit_id.

**Tech Stack:** FastAPI + SQLAlchemy (backend) · Typer + httpx (CLI) · Next.js 15 + TS (web) · Playwright (e2e) · pytest (backend/CLI).

**Spec reference:** first-principles analysis 2026-04-23. The four indicators:
1. **Retrieval utility**: success rate per ask, rank-of-useful artifact, top-1 precision.
2. **Time-to-first-useful-retrieval (TTFUR)**: seconds between agent `join` and first outcome=success for that agent.
3. **Trust propagation latency**: time between artifact publish and blessing count reaching kindred's `bless_threshold`.
4. **Staleness cost**: count of asks where the top-K ignoring expiry would have surfaced an expired artifact (opportunity cost) + count of asks where the returned artifact had `valid_until` within the next 7 days.

---

## File Structure

```
backend/src/kindred/
├── facilitator/
│   └── librarian.py                 # MODIFY: retrieve_top_k returns (scored, expired_shadow_count)
├── api/
│   ├── routers/
│   │   ├── ask.py                   # MODIFY: richer audit payload (scores, expired_shadow_hits)
│   │   ├── outcomes.py              # MODIFY: accept chosen_content_id, persist to outcome_reported event
│   │   └── health.py                # CREATE: GET /v1/kindreds/{slug}/health
│   └── schemas/
│       ├── outcomes.py              # MODIFY: add chosen_content_id field
│       └── health.py                # CREATE: KindredHealthResp
├── services/
│   └── health.py                    # CREATE: compute 4 indicators from audit_log + events + artifacts
└── facilitator/
    └── outcomes.py                  # MODIFY: accept chosen_content_id; include in outcome_reported event

backend/tests/
├── unit/
│   ├── test_librarian.py            # MODIFY: add expired_shadow_count assertions
│   ├── test_outcomes.py             # MODIFY: chosen_content_id propagation
│   └── test_services_health.py      # CREATE: unit tests for each indicator
├── api/
│   ├── test_ask_api.py              # MODIFY: assert richer payload
│   ├── test_outcomes_api.py         # MODIFY: accept chosen_content_id
│   └── test_health_api.py           # CREATE: endpoint tests

cli/src/kindred_client/
├── api_client.py                    # MODIFY: add report_outcome(audit_id, result, chosen_content_id)
├── commands/
│   ├── report.py                    # CREATE: `kin report <audit_id> <result> [--chose <cid>]`
│   └── save.py                      # MODIFY: replace stub with history-scan + auto-report
└── cli.py                           # MODIFY: register report_cmd

cli/tests/
├── test_report_command.py           # CREATE
└── test_save_command.py             # CREATE (replaces current placeholder if any)

claude-code-plugin/
├── hooks/
│   └── post_tool_use.sh             # MODIFY: write audit_id into history entry; call `kin save`
└── skills/
    └── kindred-retrieval.md         # MODIFY: instruct agents to emit the last audit_id sentinel

web/src/
├── app/
│   └── dashboard/[slug]/health/
│       ├── page.tsx                 # CREATE: health dashboard SSR page
│       └── loading.tsx              # CREATE
├── components/
│   └── health/
│       ├── IndicatorCard.tsx        # CREATE
│       ├── RetrievalUtilityPanel.tsx# CREATE
│       ├── TTFURPanel.tsx           # CREATE
│       ├── TrustLatencyPanel.tsx    # CREATE
│       └── StalenessPanel.tsx       # CREATE
└── lib/
    └── backend.ts                   # MODIFY: add fetchHealth(slug)

web/tests/
└── health.spec.ts                   # CREATE (Playwright)

scripts/
└── onboarding_benchmark.sh          # MODIFY: measure TTFUR, not TTI
```

---

## Phase 1 — Retrieval telemetry enrichment (backend)

### Task 1: Extend `retrieve_top_k` with expired-shadow count

**Files:**
- Modify: `backend/src/kindred/facilitator/librarian.py`
- Modify: `backend/tests/unit/test_librarian.py`

**Why:** Staleness cost indicator requires knowing how many of the top-K (if we *had not* filtered by expiry) would have been expired. This is the "opportunity cost" signal.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_librarian.py`:

```python
@pytest.mark.asyncio
async def test_retrieve_top_k_returns_expired_shadow_count(session, kindred, provider):
    """retrieve_top_k returns (scored, expired_shadow_count) — the number of
    top-K matches that would have surfaced if expiry filter were disabled."""
    now = datetime.now(UTC)
    expired = await _make_artifact(
        session, kindred_id=kindred.id, logical_name="stale",
        valid_from=now - timedelta(days=60),
        valid_until=now - timedelta(days=1),   # expired
        embedding=[1.0, 0.0, 0.0],
    )
    fresh = await _make_artifact(
        session, kindred_id=kindred.id, logical_name="fresh",
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=30),
        embedding=[0.0, 1.0, 0.0],
    )
    await session.flush()

    provider.set_fixed_vector([1.0, 0.0, 0.0])
    scored, expired_shadow = await retrieve_top_k(
        session, kindred_id=kindred.id, query="stale topic",
        provider=provider, k=5,
    )
    assert [a.content_id for a, _ in scored] == [fresh.content_id]
    assert expired_shadow == 1   # `expired` would have been top-1 without filter
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_librarian.py::test_retrieve_top_k_returns_expired_shadow_count -v`
Expected: FAIL — signature mismatch (returns list, not tuple).

- [ ] **Step 3: Modify `retrieve_top_k` to also return shadow count**

Replace the function body in `backend/src/kindred/facilitator/librarian.py`:

```python
async def retrieve_top_k(
    session: AsyncSession,
    *,
    kindred_id: UUID,
    query: str,
    provider: EmbeddingProvider,
    k: int = 5,
    include_expired: bool = False,
) -> tuple[list[tuple[Artifact, float]], int]:
    """Return ((artifact, similarity) top-K, expired_shadow_count).

    expired_shadow_count: count of artefacts that WOULD have been in the top-K
    if the expiry filter were disabled. Zero when include_expired=True.
    """
    query_vec = await provider.embed(query)
    now = datetime.now(UTC)

    # Load all artefacts regardless of expiry — we're already scanning the full
    # corpus in Python (cosine), so filtering is free.
    stmt = select(Artifact).where(Artifact.kindred_id == kindred_id)
    artifacts = list((await session.execute(stmt)).scalars())

    scored_all: list[tuple[Artifact, float]] = []
    for art in artifacts:
        if art.embedding is None:
            continue
        scored_all.append((art, _cosine(query_vec, art.embedding)))
    scored_all.sort(key=lambda p: p[1], reverse=True)

    if include_expired:
        return scored_all[:k], 0

    top_k_with_expired = scored_all[:k]
    expired_shadow = sum(1 for a, _ in top_k_with_expired if a.valid_until <= now)
    scored_fresh = [(a, s) for a, s in scored_all if a.valid_until > now][:k]
    return scored_fresh, expired_shadow
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/test_librarian.py -v`
Expected: PASS (all existing librarian tests still green — update any that assert the old return shape).

- [ ] **Step 5: Fix callers of the old signature**

Search: `cd backend && uv run grep -rn "retrieve_top_k(" src/ tests/`
Update every non-test caller to destructure the tuple. Currently only one in `src/`: `api/routers/ask.py` — handled in Task 2.

For existing `test_librarian.py` tests that assert a plain list, change `scored = await retrieve_top_k(...)` → `scored, _ = await retrieve_top_k(...)`.

Run: `cd backend && uv run pytest tests/unit/test_librarian.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/kindred/facilitator/librarian.py backend/tests/unit/test_librarian.py
git commit -m "feat(backend): retrieve_top_k returns expired-shadow count for staleness telemetry"
```

---

### Task 2: Enrich `/ask` audit payload

**Files:**
- Modify: `backend/src/kindred/api/routers/ask.py`
- Modify: `backend/tests/api/test_ask_api.py`

**Why:** Retrieval-utility indicator needs per-ask metadata: similarity scores for each returned artifact, tier distribution, and expired-shadow count.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/api/test_ask_api.py`:

```python
@pytest.mark.asyncio
async def test_ask_audit_payload_includes_retrieval_metadata(async_client, seeded_kindred, agent_ctx):
    """Audit payload records scores, tiers, and expired-shadow count per ask."""
    resp = await async_client.post(
        f"/v1/kindreds/{seeded_kindred.slug}/ask",
        json={"query": "how do I structure commits", "k": 3},
        headers={"X-Agent-Pubkey": agent_ctx.pubkey_str},
    )
    assert resp.status_code == 200
    body = resp.json()
    audit_id = body["audit_id"]

    # Load the audit row directly and assert payload shape.
    async with agent_ctx.session() as s:
        audit = (await s.execute(
            select(AuditLog).where(AuditLog.id == UUID(audit_id))
        )).scalar_one()
    p = audit.payload
    assert "scores" in p and isinstance(p["scores"], list)
    assert "tiers" in p and isinstance(p["tiers"], list)
    assert "expired_shadow_hits" in p and isinstance(p["expired_shadow_hits"], int)
    assert len(p["scores"]) == len(p["artifact_ids_returned"])
    assert len(p["tiers"]) == len(p["artifact_ids_returned"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/api/test_ask_api.py::test_ask_audit_payload_includes_retrieval_metadata -v`
Expected: FAIL — keys missing.

- [ ] **Step 3: Update `ask.py` router**

In `backend/src/kindred/api/routers/ask.py`, replace the `retrieve_top_k` call + `append_audit` payload:

```python
    scored, expired_shadow = await retrieve_top_k(
        session, kindred_id=k.id, query=q, provider=provider, k=req.k,
    )
    with_tier: list[tuple[Artifact, float, str]] = []
    for art, score in scored:
        tier = await compute_tier(session, artifact=art, threshold=k.bless_threshold)
        with_tier.append((art, score, tier))

    filtered = filter_by_tier(
        [(a, t) for a, _s, t in with_tier],
        include_peer_shared=req.include_peer_shared,
    )
    # Re-align score list with the filtered order.
    score_by_cid = {a.content_id: s for a, s, _t in with_tier}
    tier_by_cid = {a.content_id: t for a, _s, t in with_tier}
```

Then replace the `append_audit(...)` payload block:

```python
    audit = await append_audit(
        session, kindred_id=k.id, agent_pubkey=agent_pubkey,
        action="ask",
        payload={
            "query": q,
            "artifact_ids_returned": [a.content_id for a, _ in filtered],
            "scores": [score_by_cid[a.content_id] for a, _ in filtered],
            "tiers": [tier_by_cid[a.content_id] for a, _ in filtered],
            "k": req.k,
            "expired_shadow_hits": expired_shadow,
            "blocked_injection": False,
        },
        facilitator_sk=settings.facilitator_signing_key,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/api/test_ask_api.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/kindred/api/routers/ask.py backend/tests/api/test_ask_api.py
git commit -m "feat(backend): enrich /ask audit payload with scores, tiers, expired-shadow count"
```

---

### Task 3: Outcome reporting accepts `chosen_content_id`

**Files:**
- Modify: `backend/src/kindred/api/schemas/outcomes.py`
- Modify: `backend/src/kindred/facilitator/outcomes.py`
- Modify: `backend/src/kindred/api/routers/outcomes.py`
- Modify: `backend/tests/unit/test_outcomes.py`
- Modify: `backend/tests/api/test_outcomes_api.py`

**Why:** Rank-of-useful artifact is the key retrieval-quality metric. If the agent always picks position 3 of 5, the ranker is off. Today we only know "success/fail" for the whole set.

- [ ] **Step 1: Write the failing unit test**

Append to `backend/tests/unit/test_outcomes.py`:

```python
@pytest.mark.asyncio
async def test_report_outcome_with_chosen_content_id(session, seeded_ask_audit):
    """outcome_reported event records which content_id the agent actually used."""
    audit = seeded_ask_audit
    await report_outcome(
        session, audit_id=audit.id, result="success",
        notes="used the commit-convention doc", chosen_content_id="ART-abc123",
    )
    await session.commit()

    evts = (await session.execute(
        select(Event).where(
            Event.kindred_id == audit.kindred_id,
            Event.event_type == "outcome_reported",
        )
    )).scalars().all()
    assert len(evts) == 1
    assert evts[0].payload["chosen_content_id"] == "ART-abc123"
    assert evts[0].payload["result"] == "success"
```

- [ ] **Step 2: Run it to confirm failure**

Run: `cd backend && uv run pytest tests/unit/test_outcomes.py::test_report_outcome_with_chosen_content_id -v`
Expected: FAIL — `report_outcome()` doesn't accept `chosen_content_id`.

- [ ] **Step 3: Update schema**

Replace `backend/src/kindred/api/schemas/outcomes.py`:

```python
from pydantic import BaseModel


class ReportOutcomeReq(BaseModel):
    audit_id: str
    result: str
    notes: str = ""
    chosen_content_id: str | None = None
```

- [ ] **Step 4: Update service function**

Replace `report_outcome` in `backend/src/kindred/facilitator/outcomes.py`:

```python
async def report_outcome(
    session: AsyncSession, *, audit_id: UUID, result: str | OutcomeResult,
    notes: str = "", chosen_content_id: str | None = None,
) -> None:
    try:
        parsed = OutcomeResult(result)
    except ValueError as e:
        raise ValidationError(f"invalid outcome result: {result!r}") from e

    audit = (
        await session.execute(select(AuditLog).where(AuditLog.id == audit_id))
    ).scalar_one_or_none()
    if audit is None:
        raise NotFoundError(f"audit {audit_id} not found")

    cids: list[str] = list(audit.payload.get("artifact_ids_returned", []) or [])

    # Validate chosen_content_id is one of the returned artifacts (if given).
    if chosen_content_id is not None and chosen_content_id not in cids:
        raise ValidationError(
            f"chosen_content_id {chosen_content_id!r} was not in audit's returned set"
        )

    is_success = parsed in _SUCCESS_VALUES
    for cid in cids:
        stmt = (
            update(Artifact)
            .where(Artifact.content_id == cid)
            .values(
                outcome_uses=Artifact.outcome_uses + 1,
                outcome_successes=Artifact.outcome_successes + (1 if is_success else 0),
            )
        )
        await session.execute(stmt)

    await append_event(
        session, kindred_id=audit.kindred_id, event_type="outcome_reported",
        payload={
            "audit_id": str(audit_id),
            "result": parsed.value,
            "notes": notes,
            "artifact_ids": cids,
            "chosen_content_id": chosen_content_id,
            "rank_of_chosen": cids.index(chosen_content_id) if chosen_content_id else None,
        },
    )
    await session.flush()
```

- [ ] **Step 5: Update router**

Replace `backend/src/kindred/api/routers/outcomes.py`:

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session
from kindred.api.schemas.outcomes import ReportOutcomeReq
from kindred.facilitator.outcomes import report_outcome

router = APIRouter()


@router.post("/outcome", status_code=200)
async def outcome(
    req: ReportOutcomeReq,
    session: AsyncSession = Depends(db_session),
):
    try:
        audit_id = UUID(req.audit_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await report_outcome(
        session, audit_id=audit_id, result=req.result,
        notes=req.notes, chosen_content_id=req.chosen_content_id,
    )
    return {"ok": True}
```

- [ ] **Step 6: Write the API test**

Append to `backend/tests/api/test_outcomes_api.py`:

```python
@pytest.mark.asyncio
async def test_outcome_api_records_chosen_content_id(async_client, seeded_ask_context):
    audit_id, returned_cids = seeded_ask_context
    chosen = returned_cids[1]
    resp = await async_client.post(
        "/v1/ask/outcome",
        json={"audit_id": str(audit_id), "result": "success", "chosen_content_id": chosen},
    )
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_outcome_api_rejects_unknown_chosen_content_id(async_client, seeded_ask_context):
    audit_id, _cids = seeded_ask_context
    resp = await async_client.post(
        "/v1/ask/outcome",
        json={"audit_id": str(audit_id), "result": "success", "chosen_content_id": "ART-not-in-set"},
    )
    assert resp.status_code == 400
```

- [ ] **Step 7: Run tests to confirm pass**

Run: `cd backend && uv run pytest tests/unit/test_outcomes.py tests/api/test_outcomes_api.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/src/kindred/api/schemas/outcomes.py backend/src/kindred/facilitator/outcomes.py backend/src/kindred/api/routers/outcomes.py backend/tests/unit/test_outcomes.py backend/tests/api/test_outcomes_api.py
git commit -m "feat(backend): outcome reports include chosen_content_id for rank-of-useful telemetry"
```

---

## Phase 2 — Health service & endpoint (backend)

### Task 4: Create `kindred.services.health` — indicator computations

**Files:**
- Create: `backend/src/kindred/services/health.py`
- Create: `backend/src/kindred/api/schemas/health.py`
- Create: `backend/tests/unit/test_services_health.py`

**Why:** One module, one responsibility per function — each indicator is computable from existing tables alone. Keeping this in `services/` (not `facilitator/`) makes it available to any caller.

- [ ] **Step 1: Write the failing test (retrieval utility)**

Create `backend/tests/unit/test_services_health.py`:

```python
"""Unit tests for kindred.services.health — each indicator in isolation."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from kindred.models.artifact import Artifact
from kindred.models.audit import AuditLog
from kindred.models.event import Event
from kindred.services.health import (
    compute_retrieval_utility,
    compute_staleness_cost,
    compute_trust_propagation,
    compute_ttfur,
)


@pytest.mark.asyncio
async def test_retrieval_utility_success_rate_and_mrr(session, kindred, agent_ctx):
    """Computes: total_asks, total_outcomes, success_rate, mean_rank_of_chosen."""
    # Seed 3 asks; 2 outcomes reported (1 success @ rank 0, 1 success @ rank 2).
    a1 = await _seed_ask_with_outcome(session, kindred, agent_ctx, ["X","Y","Z"],
                                      chosen="X", result="success")
    a2 = await _seed_ask_with_outcome(session, kindred, agent_ctx, ["A","B","C"],
                                      chosen="C", result="success")
    await _seed_ask_without_outcome(session, kindred, agent_ctx, ["P","Q"])

    result = await compute_retrieval_utility(session, kindred_id=kindred.id)
    assert result.total_asks == 3
    assert result.total_outcomes == 2
    assert result.success_rate == 1.0        # both outcomes succeeded
    assert result.mean_rank_of_chosen == 1.0 # mean(0, 2)
    assert result.top1_precision == 0.5      # 1 of 2 outcomes chose rank 0
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/unit/test_services_health.py -v`
Expected: FAIL — `kindred.services.health` does not exist.

- [ ] **Step 3: Create schema**

Create `backend/src/kindred/api/schemas/health.py`:

```python
from pydantic import BaseModel


class RetrievalUtility(BaseModel):
    total_asks: int
    total_outcomes: int
    success_rate: float          # successes / outcomes (0.0 when no outcomes)
    mean_rank_of_chosen: float   # avg zero-indexed rank (0.0 when no outcomes)
    top1_precision: float        # fraction of outcomes where rank_of_chosen == 0


class TTFUR(BaseModel):
    sample_size: int
    p50_seconds: float | None
    p90_seconds: float | None


class TrustPropagation(BaseModel):
    promoted_artifacts: int      # artefacte that hit bless_threshold
    p50_seconds: float | None    # median publish → tier-blessed
    p90_seconds: float | None


class StalenessCost(BaseModel):
    shadow_hits_last_7d: int     # asks where expired artefact would have made top-K
    expiring_soon_hits_last_7d: int  # asks where returned artifact expires within 7d


class KindredHealthResp(BaseModel):
    kindred_slug: str
    generated_at: str            # ISO 8601 UTC
    retrieval_utility: RetrievalUtility
    ttfur: TTFUR
    trust_propagation: TrustPropagation
    staleness_cost: StalenessCost
```

- [ ] **Step 4: Implement `compute_retrieval_utility`**

Create `backend/src/kindred/services/health.py`:

```python
"""Compute network-health indicators from audit_log + events + artifacts.

Zero schema changes. Every indicator is a read-only aggregation, safe to call
from a public endpoint because it never exposes agent pubkeys or query text —
only aggregate counts and percentiles.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from statistics import median
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.schemas.health import (
    RetrievalUtility,
    StalenessCost,
    TrustPropagation,
    TTFUR,
)
from kindred.models.artifact import Artifact, Blessing
from kindred.models.audit import AuditLog
from kindred.models.event import Event
from kindred.models.kindred import Kindred


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round(q * (len(ordered) - 1)))))
    return ordered[idx]


async def compute_retrieval_utility(
    session: AsyncSession, *, kindred_id: UUID,
) -> RetrievalUtility:
    asks_q = select(AuditLog).where(
        AuditLog.kindred_id == kindred_id,
        AuditLog.action == "ask",
    )
    asks = list((await session.execute(asks_q)).scalars())
    total_asks = sum(1 for a in asks if not a.payload.get("blocked_injection"))

    outcomes_q = select(Event).where(
        Event.kindred_id == kindred_id,
        Event.event_type == "outcome_reported",
    )
    outcomes = list((await session.execute(outcomes_q)).scalars())

    successes = [o for o in outcomes if o.payload.get("result") in ("success", "partial")]
    ranks = [o.payload["rank_of_chosen"] for o in successes
             if o.payload.get("rank_of_chosen") is not None]

    return RetrievalUtility(
        total_asks=total_asks,
        total_outcomes=len(outcomes),
        success_rate=(len(successes) / len(outcomes)) if outcomes else 0.0,
        mean_rank_of_chosen=(sum(ranks) / len(ranks)) if ranks else 0.0,
        top1_precision=(sum(1 for r in ranks if r == 0) / len(ranks)) if ranks else 0.0,
    )
```

- [ ] **Step 5: Add test helpers**

Append helpers to `backend/tests/unit/test_services_health.py` (top of file):

```python
async def _seed_ask_with_outcome(session, kindred, agent_ctx, cids, *, chosen, result):
    """Creates a ask audit with given returned cids, then an outcome_reported event."""
    from kindred.models.audit import AuditLog
    from kindred.models.event import Event
    audit = AuditLog(
        kindred_id=kindred.id, agent_pubkey=agent_ctx.pubkey, action="ask",
        payload={"query": "q", "artifact_ids_returned": cids, "scores": [1.0]*len(cids),
                 "tiers": ["peer-shared"]*len(cids), "k": len(cids),
                 "expired_shadow_hits": 0, "blocked_injection": False},
        facilitator_sig=b"x"*64, seq=await _next_audit_seq(session, kindred.id),
    )
    session.add(audit)
    await session.flush()
    evt = Event(
        kindred_id=kindred.id,
        seq=await _next_event_seq(session, kindred.id),
        event_type="outcome_reported",
        payload={"audit_id": str(audit.id), "result": result, "notes": "",
                 "artifact_ids": cids, "chosen_content_id": chosen,
                 "rank_of_chosen": cids.index(chosen)},
    )
    session.add(evt)
    await session.flush()
    return audit


async def _seed_ask_without_outcome(session, kindred, agent_ctx, cids):
    from kindred.models.audit import AuditLog
    audit = AuditLog(
        kindred_id=kindred.id, agent_pubkey=agent_ctx.pubkey, action="ask",
        payload={"query": "q", "artifact_ids_returned": cids, "scores": [1.0]*len(cids),
                 "tiers": ["peer-shared"]*len(cids), "k": len(cids),
                 "expired_shadow_hits": 0, "blocked_injection": False},
        facilitator_sig=b"x"*64, seq=await _next_audit_seq(session, kindred.id),
    )
    session.add(audit)
    await session.flush()
    return audit


async def _next_audit_seq(session, kindred_id):
    from kindred.models.audit import AuditLog
    q = select(func.coalesce(func.max(AuditLog.seq), 0) + 1).where(
        AuditLog.kindred_id == kindred_id,
    )
    return (await session.execute(q)).scalar_one()


async def _next_event_seq(session, kindred_id):
    from kindred.models.event import Event
    q = select(func.coalesce(func.max(Event.seq), 0) + 1).where(
        Event.kindred_id == kindred_id,
    )
    return (await session.execute(q)).scalar_one()
```

- [ ] **Step 6: Run the retrieval-utility test**

Run: `cd backend && uv run pytest tests/unit/test_services_health.py::test_retrieval_utility_success_rate_and_mrr -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/kindred/services/health.py backend/src/kindred/api/schemas/health.py backend/tests/unit/test_services_health.py
git commit -m "feat(backend): compute_retrieval_utility — success rate, MRR, top-1 precision"
```

---

### Task 5: Implement `compute_ttfur`

**Files:**
- Modify: `backend/src/kindred/services/health.py`
- Modify: `backend/tests/unit/test_services_health.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_services_health.py`:

```python
@pytest.mark.asyncio
async def test_ttfur_measures_join_to_first_success(session, kindred):
    """TTFUR = first outcome=success timestamp − agent membership created_at,
    per agent that has both. Report p50/p90 over agents."""
    now = datetime.now(UTC)
    # Agent A: joined at T0, first success 30s later
    a = await _seed_agent_with_join_and_success(
        session, kindred, join_at=now - timedelta(minutes=10),
        success_at=now - timedelta(minutes=10) + timedelta(seconds=30),
    )
    # Agent B: joined T0, first success 90s later
    b = await _seed_agent_with_join_and_success(
        session, kindred, join_at=now - timedelta(minutes=20),
        success_at=now - timedelta(minutes=20) + timedelta(seconds=90),
    )
    # Agent C: joined, no success yet — excluded from percentile
    await _seed_agent_join_only(session, kindred, join_at=now)

    result = await compute_ttfur(session, kindred_id=kindred.id)
    assert result.sample_size == 2
    assert 25.0 <= result.p50_seconds <= 95.0   # either 30 or 90 depending on picker
    assert result.p90_seconds is not None
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/unit/test_services_health.py::test_ttfur_measures_join_to_first_success -v`
Expected: FAIL — `compute_ttfur` not defined.

- [ ] **Step 3: Implement `compute_ttfur`**

Append to `backend/src/kindred/services/health.py`:

```python
from kindred.models.membership import Membership


async def compute_ttfur(
    session: AsyncSession, *, kindred_id: UUID,
) -> TTFUR:
    """Time from agent joining the kindred until their first success outcome.

    Joined = membership row exists (via agent pubkey). First success = earliest
    `outcome_reported` event with result=success|partial whose audit was
    performed by that agent_pubkey.
    """
    memberships = list((await session.execute(
        select(Membership).where(Membership.kindred_id == kindred_id)
    )).scalars())

    # Map agent_pubkey → (first_ask_audit_id, first_ask_created_at) for success outcomes.
    deltas_seconds: list[float] = []
    for m in memberships:
        # All ask audits by this agent in this kindred.
        agent_asks = list((await session.execute(
            select(AuditLog).where(
                AuditLog.kindred_id == kindred_id,
                AuditLog.agent_pubkey == m.agent_pubkey,
                AuditLog.action == "ask",
            ).order_by(AuditLog.created_at.asc())
        )).scalars())
        if not agent_asks:
            continue
        # Now find the earliest outcome_reported event that references one of these audit ids
        ask_ids = {str(a.id) for a in agent_asks}
        outcome_events = list((await session.execute(
            select(Event).where(
                Event.kindred_id == kindred_id,
                Event.event_type == "outcome_reported",
            ).order_by(Event.created_at.asc())
        )).scalars())
        first_success_at: datetime | None = None
        for e in outcome_events:
            if (e.payload.get("result") in ("success", "partial")
                    and e.payload.get("audit_id") in ask_ids):
                first_success_at = e.created_at
                break
        if first_success_at is None:
            continue
        delta = (first_success_at - m.created_at).total_seconds()
        if delta >= 0:
            deltas_seconds.append(delta)

    return TTFUR(
        sample_size=len(deltas_seconds),
        p50_seconds=_percentile(deltas_seconds, 0.5),
        p90_seconds=_percentile(deltas_seconds, 0.9),
    )
```

- [ ] **Step 4: Add test helpers for agent seeding**

Append to `backend/tests/unit/test_services_health.py`:

```python
async def _seed_agent_with_join_and_success(session, kindred, *, join_at, success_at):
    from kindred.models.membership import Membership
    pk = uuid4().bytes + b"\x00" * 16  # 32 bytes
    m = Membership(
        kindred_id=kindred.id, agent_pubkey=pk,
        scope=["read"], expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    m.created_at = join_at
    session.add(m)
    await session.flush()

    audit = AuditLog(
        kindred_id=kindred.id, agent_pubkey=pk, action="ask",
        payload={"query": "q", "artifact_ids_returned": ["X"], "scores": [1.0],
                 "tiers": ["peer-shared"], "k": 1, "expired_shadow_hits": 0,
                 "blocked_injection": False},
        facilitator_sig=b"x"*64, seq=await _next_audit_seq(session, kindred.id),
    )
    audit.created_at = success_at
    session.add(audit)
    await session.flush()

    evt = Event(
        kindred_id=kindred.id,
        seq=await _next_event_seq(session, kindred.id),
        event_type="outcome_reported",
        payload={"audit_id": str(audit.id), "result": "success",
                 "notes": "", "artifact_ids": ["X"],
                 "chosen_content_id": "X", "rank_of_chosen": 0},
    )
    evt.created_at = success_at
    session.add(evt)
    await session.flush()
    return m


async def _seed_agent_join_only(session, kindred, *, join_at):
    from kindred.models.membership import Membership
    pk = uuid4().bytes + b"\x00" * 16
    m = Membership(
        kindred_id=kindred.id, agent_pubkey=pk,
        scope=["read"], expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    m.created_at = join_at
    session.add(m)
    await session.flush()
    return m
```

(Check the Membership model fields match — adjust `scope`/`expires_at` names to whatever the model actually uses by reading `backend/src/kindred/models/membership.py` before seeding.)

- [ ] **Step 5: Run the test**

Run: `cd backend && uv run pytest tests/unit/test_services_health.py::test_ttfur_measures_join_to_first_success -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/kindred/services/health.py backend/tests/unit/test_services_health.py
git commit -m "feat(backend): compute_ttfur — time from join to first success per agent"
```

---

### Task 6: Implement `compute_trust_propagation`

**Files:**
- Modify: `backend/src/kindred/services/health.py`
- Modify: `backend/tests/unit/test_services_health.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_services_health.py`:

```python
@pytest.mark.asyncio
async def test_trust_propagation_measures_publish_to_tier_promotion(session, kindred):
    """For each artifact whose blessings reached bless_threshold, compute
    (nth_blessing.created_at − artifact.created_at) where n = threshold."""
    kindred.bless_threshold = 2
    await session.flush()
    now = datetime.now(UTC)

    # Artifact A: 2 blessings, promoted 60s after publish
    a = await _seed_artifact(session, kindred, created_at=now - timedelta(minutes=5))
    await _seed_blessing(session, a, created_at=now - timedelta(minutes=5, seconds=-30))
    await _seed_blessing(session, a, created_at=now - timedelta(minutes=4))   # +60s

    # Artifact B: 2 blessings, promoted 300s after publish
    b = await _seed_artifact(session, kindred, created_at=now - timedelta(minutes=30))
    await _seed_blessing(session, b, created_at=now - timedelta(minutes=28))
    await _seed_blessing(session, b, created_at=now - timedelta(minutes=25))  # +300s

    # Artifact C: 1 blessing only — not promoted, excluded
    c = await _seed_artifact(session, kindred, created_at=now)
    await _seed_blessing(session, c, created_at=now)

    result = await compute_trust_propagation(session, kindred_id=kindred.id, threshold=2)
    assert result.promoted_artifacts == 2
    assert result.p50_seconds is not None
    assert 55.0 <= result.p50_seconds <= 305.0
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/unit/test_services_health.py::test_trust_propagation_measures_publish_to_tier_promotion -v`
Expected: FAIL.

- [ ] **Step 3: Implement `compute_trust_propagation`**

Append to `backend/src/kindred/services/health.py`:

```python
async def compute_trust_propagation(
    session: AsyncSession, *, kindred_id: UUID, threshold: int,
) -> TrustPropagation:
    """For each artifact with >= threshold blessings, compute seconds from
    artifact.created_at to the threshold-th blessing's created_at."""
    artifacts = list((await session.execute(
        select(Artifact).where(Artifact.kindred_id == kindred_id)
    )).scalars())

    deltas: list[float] = []
    for art in artifacts:
        blessings = list((await session.execute(
            select(Blessing).where(Blessing.artifact_id == art.id)
            .order_by(Blessing.created_at.asc())
        )).scalars())
        if len(blessings) < threshold:
            continue
        nth = blessings[threshold - 1]
        delta = (nth.created_at - art.created_at).total_seconds()
        if delta >= 0:
            deltas.append(delta)

    return TrustPropagation(
        promoted_artifacts=len(deltas),
        p50_seconds=_percentile(deltas, 0.5),
        p90_seconds=_percentile(deltas, 0.9),
    )
```

- [ ] **Step 4: Add seed helpers**

Append to `backend/tests/unit/test_services_health.py`:

```python
async def _seed_artifact(session, kindred, *, created_at):
    from kindred.models.artifact import Artifact
    art = Artifact(
        content_id=f"ART-{uuid4().hex[:8]}",
        kindred_id=kindred.id,
        type="routine",
        logical_name="t",
        author_pubkey=b"x"*32,
        author_sig=b"x"*64,
        valid_from=created_at,
        valid_until=created_at + timedelta(days=365),
        tags=[],
    )
    art.created_at = created_at
    session.add(art)
    await session.flush()
    return art


async def _seed_blessing(session, artifact, *, created_at):
    from kindred.models.artifact import Blessing
    from uuid import uuid4
    b = Blessing(
        artifact_id=artifact.id,
        signer_pubkey=uuid4().bytes + b"\x00"*16,
        signer_agent_id=uuid4(),
        sig=b"x"*64,
    )
    b.created_at = created_at
    session.add(b)
    await session.flush()
    return b
```

(Note: `signer_agent_id` is a ForeignKey; either disable FK enforcement in the test DB, or seed an actual Agent row. Check `backend/tests/conftest.py` for how existing tests handle this — if agent seeding helpers exist, use them.)

- [ ] **Step 5: Run**

Run: `cd backend && uv run pytest tests/unit/test_services_health.py::test_trust_propagation_measures_publish_to_tier_promotion -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/kindred/services/health.py backend/tests/unit/test_services_health.py
git commit -m "feat(backend): compute_trust_propagation — publish→threshold-blessing latency"
```

---

### Task 7: Implement `compute_staleness_cost`

**Files:**
- Modify: `backend/src/kindred/services/health.py`
- Modify: `backend/tests/unit/test_services_health.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_services_health.py`:

```python
@pytest.mark.asyncio
async def test_staleness_cost_sums_shadow_and_expiring_soon(session, kindred, agent_ctx):
    """shadow_hits_last_7d: sum of payload.expired_shadow_hits for recent asks.
    expiring_soon_hits_last_7d: asks where any returned artifact has valid_until
    within the next 7 days."""
    now = datetime.now(UTC)

    # ask 1 (recent, 2 shadow hits, 0 expiring-soon returned)
    art_long = await _seed_artifact(session, kindred, created_at=now - timedelta(days=1))
    art_long.valid_until = now + timedelta(days=90)
    ask1 = AuditLog(
        kindred_id=kindred.id, agent_pubkey=agent_ctx.pubkey, action="ask",
        payload={"query": "q", "artifact_ids_returned": [art_long.content_id],
                 "scores": [0.8], "tiers": ["peer-shared"], "k": 1,
                 "expired_shadow_hits": 2, "blocked_injection": False},
        facilitator_sig=b"x"*64, seq=await _next_audit_seq(session, kindred.id),
    )
    ask1.created_at = now - timedelta(days=1)
    session.add(ask1)
    await session.flush()

    # ask 2 (recent, 0 shadow, returned artifact expires in 3 days)
    art_soon = await _seed_artifact(session, kindred, created_at=now - timedelta(days=1))
    art_soon.valid_until = now + timedelta(days=3)
    ask2 = AuditLog(
        kindred_id=kindred.id, agent_pubkey=agent_ctx.pubkey, action="ask",
        payload={"query": "q", "artifact_ids_returned": [art_soon.content_id],
                 "scores": [0.8], "tiers": ["peer-shared"], "k": 1,
                 "expired_shadow_hits": 0, "blocked_injection": False},
        facilitator_sig=b"x"*64, seq=await _next_audit_seq(session, kindred.id),
    )
    ask2.created_at = now - timedelta(hours=2)
    session.add(ask2)
    await session.flush()

    # ask 3 (10 days old — excluded from 7d window)
    ask3 = AuditLog(
        kindred_id=kindred.id, agent_pubkey=agent_ctx.pubkey, action="ask",
        payload={"query": "q", "artifact_ids_returned": [art_long.content_id],
                 "scores": [0.8], "tiers": ["peer-shared"], "k": 1,
                 "expired_shadow_hits": 5, "blocked_injection": False},
        facilitator_sig=b"x"*64, seq=await _next_audit_seq(session, kindred.id),
    )
    ask3.created_at = now - timedelta(days=10)
    session.add(ask3)
    await session.flush()

    result = await compute_staleness_cost(session, kindred_id=kindred.id)
    assert result.shadow_hits_last_7d == 2
    assert result.expiring_soon_hits_last_7d == 1
```

- [ ] **Step 2: Run**

Run: `cd backend && uv run pytest tests/unit/test_services_health.py::test_staleness_cost_sums_shadow_and_expiring_soon -v`
Expected: FAIL — `compute_staleness_cost` not defined.

- [ ] **Step 3: Implement**

Append to `backend/src/kindred/services/health.py`:

```python
async def compute_staleness_cost(
    session: AsyncSession, *, kindred_id: UUID,
) -> StalenessCost:
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=7)
    soon = now + timedelta(days=7)

    recent_asks = list((await session.execute(
        select(AuditLog).where(
            AuditLog.kindred_id == kindred_id,
            AuditLog.action == "ask",
            AuditLog.created_at >= cutoff,
        )
    )).scalars())

    shadow_hits = sum(a.payload.get("expired_shadow_hits", 0) or 0 for a in recent_asks)

    expiring_soon_hits = 0
    for a in recent_asks:
        cids = a.payload.get("artifact_ids_returned", []) or []
        if not cids:
            continue
        arts = list((await session.execute(
            select(Artifact).where(Artifact.content_id.in_(cids))
        )).scalars())
        if any(art.valid_until <= soon for art in arts):
            expiring_soon_hits += 1

    return StalenessCost(
        shadow_hits_last_7d=shadow_hits,
        expiring_soon_hits_last_7d=expiring_soon_hits,
    )
```

- [ ] **Step 4: Run**

Run: `cd backend && uv run pytest tests/unit/test_services_health.py -v`
Expected: all four indicator tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/kindred/services/health.py backend/tests/unit/test_services_health.py
git commit -m "feat(backend): compute_staleness_cost — shadow hits + expiring-soon returns"
```

---

### Task 8: Expose `GET /v1/kindreds/{slug}/health`

**Files:**
- Create: `backend/src/kindred/api/routers/health.py`
- Modify: `backend/src/kindred/api/main.py`
- Create: `backend/tests/api/test_health_api.py`

**Note:** Rename existing `health.py` router if needed — current `/healthz` probably lives in a different module. Check first: `grep -n "healthz" backend/src/kindred/api/routers/*.py` — if it's in `routers/health.py`, rename this new one to `routers/network_health.py` and use the prefix `/v1/kindreds` in main.py.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/api/test_health_api.py`:

```python
"""API-level tests for GET /v1/kindreds/{slug}/health."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_endpoint_returns_all_four_indicators(async_client, seeded_kindred, agent_ctx):
    resp = await async_client.get(
        f"/v1/kindreds/{seeded_kindred.slug}/health",
        headers={"X-Agent-Pubkey": agent_ctx.pubkey_str},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["kindred_slug"] == seeded_kindred.slug
    assert "retrieval_utility" in body
    assert "ttfur" in body
    assert "trust_propagation" in body
    assert "staleness_cost" in body
    assert set(body["retrieval_utility"].keys()) == {
        "total_asks", "total_outcomes", "success_rate",
        "mean_rank_of_chosen", "top1_precision",
    }


@pytest.mark.asyncio
async def test_health_endpoint_rejects_non_member(async_client, seeded_kindred, outsider_agent):
    resp = await async_client.get(
        f"/v1/kindreds/{seeded_kindred.slug}/health",
        headers={"X-Agent-Pubkey": outsider_agent.pubkey_str},
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Create the router**

Create `backend/src/kindred/api/routers/network_health.py`:

```python
"""GET /v1/kindreds/{slug}/health — network-health indicators."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session
from kindred.api.schemas.health import KindredHealthResp
from kindred.crypto.keys import str_to_pubkey
from kindred.facilitator.policy import require_agent_authorized
from kindred.services.health import (
    compute_retrieval_utility,
    compute_staleness_cost,
    compute_trust_propagation,
    compute_ttfur,
)
from kindred.services.kindreds import get_kindred_by_slug

router = APIRouter()


async def _parse_agent_pubkey(x_agent_pubkey: str = Header(...)) -> bytes:
    try:
        return str_to_pubkey(x_agent_pubkey)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.get("/{slug}/health", response_model=KindredHealthResp)
async def health(
    slug: str,
    session: AsyncSession = Depends(db_session),
    agent_pubkey: bytes = Depends(_parse_agent_pubkey),
) -> KindredHealthResp:
    k = await get_kindred_by_slug(session, slug)
    await require_agent_authorized(
        session, agent_pubkey=agent_pubkey, kindred_id=k.id,
        kindred_slug=slug, action="read",
    )
    ru = await compute_retrieval_utility(session, kindred_id=k.id)
    tt = await compute_ttfur(session, kindred_id=k.id)
    tp = await compute_trust_propagation(session, kindred_id=k.id, threshold=k.bless_threshold)
    sc = await compute_staleness_cost(session, kindred_id=k.id)
    return KindredHealthResp(
        kindred_slug=slug,
        generated_at=datetime.now(UTC).isoformat(),
        retrieval_utility=ru,
        ttfur=tt,
        trust_propagation=tp,
        staleness_cost=sc,
    )
```

- [ ] **Step 3: Register the router**

In `backend/src/kindred/api/main.py`, add the import and include:

```python
from kindred.api.routers import (
    agents, artifacts, ask, blessings, health, invites,
    kindreds, memberships, network_health, outcomes, users,
)
# ... existing includes ...
app.include_router(network_health.router, prefix="/v1/kindreds", tags=["health"])
```

- [ ] **Step 4: Run API tests**

Run: `cd backend && uv run pytest tests/api/test_health_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/kindred/api/routers/network_health.py backend/src/kindred/api/main.py backend/tests/api/test_health_api.py
git commit -m "feat(backend): GET /v1/kindreds/{slug}/health endpoint (member-auth only)"
```

---

## Phase 3 — Automatic outcome capture (CLI + plugin)

### Task 9: CLI — `kin report` command

**Files:**
- Create: `cli/src/kindred_client/commands/report.py`
- Modify: `cli/src/kindred_client/api_client.py`
- Modify: `cli/src/kindred_client/cli.py`
- Create: `cli/tests/test_report_command.py`

- [ ] **Step 1: Write the failing test**

Create `cli/tests/test_report_command.py`:

```python
"""Tests for `kin report <audit_id> <result>`."""
from __future__ import annotations

import respx
from httpx import Response
from typer.testing import CliRunner

from kindred_client.cli import app

runner = CliRunner()


@respx.mock
def test_report_success_posts_to_outcome_endpoint(tmp_path, monkeypatch, seeded_cli_config):
    monkeypatch.setenv("HOME", str(tmp_path))
    route = respx.post("http://127.0.0.1:8000/v1/ask/outcome").mock(
        return_value=Response(200, json={"ok": True})
    )
    r = runner.invoke(app, ["report", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "success",
                            "--chose", "ART-abc"])
    assert r.exit_code == 0, r.output
    assert route.called
    sent = route.calls[0].request
    body = sent.read()
    assert b"ART-abc" in body
    assert b"success" in body
```

- [ ] **Step 2: Run to verify failure**

Run: `cd cli && uv run pytest tests/test_report_command.py -v`
Expected: FAIL — no `report` command.

- [ ] **Step 3: Extend API client**

In `cli/src/kindred_client/api_client.py`, add (place near the existing `ask` method):

```python
    async def report_outcome(
        self, *, audit_id: str, result: str, notes: str = "",
        chosen_content_id: str | None = None,
    ) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/ask/outcome",
                json={
                    "audit_id": audit_id, "result": result,
                    "notes": notes, "chosen_content_id": chosen_content_id,
                },
            )
            if resp.status_code != 200:
                raise APIError(status_code=resp.status_code, message=resp.text)
            return resp.json()
```

- [ ] **Step 4: Create the command**

Create `cli/src/kindred_client/commands/report.py`:

```python
"""`kin report <audit_id> <result>` — report how useful an /ask was."""
from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel

from kindred_client.api_client import APIError, KindredAPI
from kindred_client.config import load_config

console = Console()


async def _run_report(
    audit_id: str, result: str, *, chosen: str | None, notes: str,
) -> dict:
    cfg = load_config()
    api = KindredAPI(cfg.backend_url)
    return await api.report_outcome(
        audit_id=audit_id, result=result,
        notes=notes, chosen_content_id=chosen,
    )


def register(app: typer.Typer) -> None:
    @app.command("report")
    def report_cmd(
        audit_id: str = typer.Argument(..., help="Audit ID from a prior `kin ask`"),
        result: str = typer.Argument(
            ..., help="One of: success | partial | fail | overridden"
        ),
        chose: str | None = typer.Option(
            None, "--chose", help="content_id of the artifact the agent actually used"
        ),
        notes: str = typer.Option("", "--notes", help="Free-text note"),
    ) -> None:
        """Report how useful the artifacts returned by a previous ask were."""
        try:
            asyncio.run(_run_report(audit_id, result, chosen=chose, notes=notes))
        except APIError as e:
            console.print(Panel.fit(
                f"[red]Backend error[/red]: {e.message}",
                title=f"HTTP {e.status_code}", border_style="red",
            ))
            raise typer.Exit(code=1) from e
        console.print(Panel.fit(
            f"[green]Outcome reported[/green]: {result}"
            + (f" (chose {chose})" if chose else ""),
            border_style="green",
        ))
```

- [ ] **Step 5: Register in the CLI**

In `cli/src/kindred_client/cli.py`, add:

```python
from kindred_client.commands import report as report_cmd
# ... after existing registrations ...
report_cmd.register(app)
```

- [ ] **Step 6: Run**

Run: `cd cli && uv run pytest tests/test_report_command.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add cli/src/kindred_client/commands/report.py cli/src/kindred_client/api_client.py cli/src/kindred_client/cli.py cli/tests/test_report_command.py
git commit -m "feat(cli): add `kin report` to submit outcome with chosen artifact"
```

---

### Task 10: Replace `kin save` stub with history-scan + auto-report

**Files:**
- Modify: `cli/src/kindred_client/commands/save.py`
- Create: `cli/tests/test_save_command.py`

**Why:** The plugin PostToolUse hook writes success snippets to `~/.kin/history/*.json` but no consumer picks them up. Wire `kin save` so it finds the most recent unconsumed history entry, locates its audit_id (from the snippet or a sidecar), and calls `kin report`.

**Design:** The history file format (today) is `{tool, exit_code, timestamp, output_snippet}`. We need `audit_id` in there too. Extend the hook to write `audit_id` when present — pulled from env var `KINDRED_LAST_AUDIT_ID` which the MCP server sets after each `/ask` call (see Task 11).

- [ ] **Step 1: Write the failing test**

Create `cli/tests/test_save_command.py`:

```python
"""Tests for `kin save this` — auto-reports latest history entry with an audit_id."""
from __future__ import annotations

import json
from pathlib import Path

import respx
from httpx import Response
from typer.testing import CliRunner

from kindred_client.cli import app

runner = CliRunner()


@respx.mock
def test_save_picks_latest_unconsumed_history_and_reports(tmp_path, monkeypatch, seeded_cli_config):
    monkeypatch.setenv("HOME", str(tmp_path))
    hist = tmp_path / ".kin" / "history"
    hist.mkdir(parents=True)
    (hist / "20260423T101500Z.json").write_text(json.dumps({
        "tool": "Bash", "exit_code": "0", "timestamp": "20260423T101500Z",
        "output_snippet": "12 passed",
        "audit_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    }))
    route = respx.post("http://127.0.0.1:8000/v1/ask/outcome").mock(
        return_value=Response(200, json={"ok": True})
    )
    r = runner.invoke(app, ["save", "this"])
    assert r.exit_code == 0, r.output
    assert route.called
    # Entry should be marked consumed (renamed with .consumed suffix).
    entries = list(hist.iterdir())
    assert any(p.name.endswith(".consumed") for p in entries)


def test_save_no_history_exits_cleanly(tmp_path, monkeypatch, seeded_cli_config):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".kin" / "history").mkdir(parents=True)
    r = runner.invoke(app, ["save", "this"])
    assert r.exit_code == 0
    assert "no history" in r.output.lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd cli && uv run pytest tests/test_save_command.py -v`
Expected: FAIL — stub returns placeholder.

- [ ] **Step 3: Replace `save.py`**

Replace `cli/src/kindred_client/commands/save.py`:

```python
"""`kin save this` — scan ~/.kin/history for the latest unconsumed success
entry and report it as outcome=success."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from kindred_client.api_client import APIError, KindredAPI
from kindred_client.config import load_config

console = Console()


def _history_dir() -> Path:
    return Path.home() / ".kin" / "history"


def _latest_unconsumed(hist: Path) -> Path | None:
    if not hist.exists():
        return None
    candidates = sorted(
        [p for p in hist.iterdir() if p.suffix == ".json"],
        key=lambda p: p.name,
        reverse=True,
    )
    return candidates[0] if candidates else None


async def _run_save() -> str | None:
    entry = _latest_unconsumed(_history_dir())
    if entry is None:
        return None
    data = json.loads(entry.read_text())
    audit_id = data.get("audit_id")
    if not audit_id:
        entry.rename(entry.with_suffix(".json.consumed"))
        return "no-audit"

    cfg = load_config()
    api = KindredAPI(cfg.backend_url)
    await api.report_outcome(
        audit_id=audit_id, result="success",
        notes=data.get("output_snippet", "")[:200],
    )
    entry.rename(entry.with_suffix(".json.consumed"))
    return audit_id


def register(app: typer.Typer) -> None:
    @app.command("save")
    def save_cmd(
        what: str = typer.Argument("this", help="Currently only 'this'"),
    ) -> None:
        """Report the latest PostToolUse success as a Kindred outcome."""
        try:
            reported = asyncio.run(_run_save())
        except APIError as e:
            console.print(Panel.fit(
                f"[red]Backend error[/red]: {e.message}",
                title=f"HTTP {e.status_code}", border_style="red",
            ))
            raise typer.Exit(code=1) from e
        if reported is None:
            console.print("[yellow]No history to save.[/yellow]")
            return
        if reported == "no-audit":
            console.print("[yellow]History entry has no audit_id (not from Kindred ask).[/yellow]")
            return
        console.print(f"[green]Reported outcome=success for audit {reported}[/green]")
```

- [ ] **Step 4: Run**

Run: `cd cli && uv run pytest tests/test_save_command.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cli/src/kindred_client/commands/save.py cli/tests/test_save_command.py
git commit -m "feat(cli): kin save reports latest ~/.kin/history entry as outcome=success"
```

---

### Task 11: Plugin — write `audit_id` into history entries

**Files:**
- Modify: `claude-code-plugin/hooks/post_tool_use.sh`
- Modify: `claude-code-plugin/skills/kindred-retrieval.md`
- Modify: `claude-code-plugin/mcp/src/` (the MCP server module that handles `kindred_ask`)

**Why:** For `kin save` to attribute success, it needs the `audit_id` in the JSON. The MCP server receives it in the `/ask` response — it must write it to a sentinel file the hook can read.

- [ ] **Step 1: Inspect MCP server structure**

Run: `ls claude-code-plugin/mcp/src`
Identify the module that calls `/v1/kindreds/{slug}/ask`. Likely `kindred_mcp/server.py` or similar. Open it.

- [ ] **Step 2: After each successful /ask, write `~/.kin/last_audit_id`**

In the MCP server's ask-tool handler, after receiving the `audit_id` from the backend:

```python
from pathlib import Path

def _write_last_audit_id(audit_id: str) -> None:
    p = Path.home() / ".kin" / "last_audit_id"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(audit_id)
```

Call `_write_last_audit_id(resp["audit_id"])` after the ask returns.

- [ ] **Step 3: Extend `post_tool_use.sh` to include `audit_id` in history JSON**

Replace the `python3` heredoc block in `claude-code-plugin/hooks/post_tool_use.sh`:

```bash
AUDIT_ID_FILE="${HOME}/.kin/last_audit_id"
AUDIT_ID=""
if [[ -f "$AUDIT_ID_FILE" ]]; then
    AUDIT_ID="$(cat "$AUDIT_ID_FILE" 2>/dev/null || true)"
fi

python3 - "$TOOL" "$EXIT_CODE" "$TS" "$SNIPPET_FILE" "$HIST_DIR/$TS.json" "$AUDIT_ID" <<'PY'
import json, sys, pathlib
tool, exit_code, ts, snippet_path, out_path, audit_id = sys.argv[1:7]
snippet = pathlib.Path(snippet_path).read_text(errors="replace")
pathlib.Path(out_path).write_text(json.dumps({
    "tool": tool,
    "exit_code": exit_code,
    "timestamp": ts,
    "output_snippet": snippet,
    "audit_id": audit_id or None,
}))
PY

# Rotate the sentinel so one audit_id isn't credited twice.
rm -f "$AUDIT_ID_FILE" || true
```

- [ ] **Step 4: Write plugin test**

In `claude-code-plugin/tests/`, add `test_post_tool_use_includes_audit_id.sh` (or the equivalent test harness the plugin uses — check existing tests first):

```bash
#!/usr/bin/env bash
set -euo pipefail

TMP=$(mktemp -d)
export HOME="$TMP"
mkdir -p "$HOME/.kin"
echo "test-audit-uuid" > "$HOME/.kin/last_audit_id"

export CLAUDE_TOOL_NAME=Bash
export CLAUDE_TOOL_EXIT_CODE=0
export CLAUDE_TOOL_OUTPUT="12 passed"

bash "$(dirname "$0")/../hooks/post_tool_use.sh"

FILE=$(ls "$HOME/.kin/history/"*.json | head -1)
grep -q "test-audit-uuid" "$FILE"
[[ ! -f "$HOME/.kin/last_audit_id" ]]   # rotated
echo "OK"
```

Make executable: `chmod +x claude-code-plugin/tests/test_post_tool_use_includes_audit_id.sh`

- [ ] **Step 5: Run plugin test**

Run: `bash claude-code-plugin/tests/test_post_tool_use_includes_audit_id.sh`
Expected: PASS (prints `OK`).

- [ ] **Step 6: Update skill docs**

In `claude-code-plugin/skills/kindred-retrieval.md`, add a section:

```markdown
## Automatic outcome reporting

When the Kindred MCP server answers an `ask`, it writes the returned
`audit_id` to `~/.kin/last_audit_id`. The PostToolUse hook picks it up
and embeds it in the history entry. `kin save this` then reports the
outcome. Agents don't need to call `kin report` manually in the common
success path — just run the task and let the hook+CLI loop attribute
credit.
```

- [ ] **Step 7: Commit**

```bash
git add claude-code-plugin/hooks/post_tool_use.sh claude-code-plugin/skills/kindred-retrieval.md claude-code-plugin/tests/test_post_tool_use_includes_audit_id.sh claude-code-plugin/mcp/src
git commit -m "feat(plugin): auto-propagate audit_id from MCP ask → post_tool_use → kin save"
```

---

## Phase 4 — Web health dashboard

### Task 12: Backend proxy + fetch helper

**Files:**
- Modify: `web/src/lib/backend.ts`

**Why:** The web app proxies all backend calls through `/api/backend/[...path]`. We add a typed helper for the new endpoint.

- [ ] **Step 1: Add `fetchKindredHealth` helper**

In `web/src/lib/backend.ts`, append:

```typescript
export type KindredHealth = {
  kindred_slug: string;
  generated_at: string;
  retrieval_utility: {
    total_asks: number;
    total_outcomes: number;
    success_rate: number;
    mean_rank_of_chosen: number;
    top1_precision: number;
  };
  ttfur: {
    sample_size: number;
    p50_seconds: number | null;
    p90_seconds: number | null;
  };
  trust_propagation: {
    promoted_artifacts: number;
    p50_seconds: number | null;
    p90_seconds: number | null;
  };
  staleness_cost: {
    shadow_hits_last_7d: number;
    expiring_soon_hits_last_7d: number;
  };
};

export async function fetchKindredHealth(
  slug: string,
  agentPubkey: string,
): Promise<KindredHealth> {
  const res = await fetch(`/api/backend/v1/kindreds/${slug}/health`, {
    headers: { "X-Agent-Pubkey": agentPubkey },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`health fetch failed: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/lib/backend.ts
git commit -m "feat(web): typed fetchKindredHealth helper"
```

---

### Task 13: Health page + indicator components

**Files:**
- Create: `web/src/app/dashboard/[slug]/health/page.tsx`
- Create: `web/src/app/dashboard/[slug]/health/loading.tsx`
- Create: `web/src/components/health/IndicatorCard.tsx`
- Create: `web/src/components/health/RetrievalUtilityPanel.tsx`
- Create: `web/src/components/health/TTFURPanel.tsx`
- Create: `web/src/components/health/TrustLatencyPanel.tsx`
- Create: `web/src/components/health/StalenessPanel.tsx`

- [ ] **Step 1: Create `IndicatorCard.tsx`**

```tsx
// web/src/components/health/IndicatorCard.tsx
type Props = {
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "good" | "warn";
};

export function IndicatorCard({ label, value, hint, tone = "neutral" }: Props) {
  const toneClass = {
    neutral: "border-neutral-300 bg-white",
    good: "border-green-500 bg-green-50",
    warn: "border-amber-500 bg-amber-50",
  }[tone];
  return (
    <div className={`rounded-lg border p-4 ${toneClass}`}>
      <div className="text-xs uppercase tracking-wide text-neutral-600">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      {hint && <div className="mt-1 text-xs text-neutral-500">{hint}</div>}
    </div>
  );
}
```

- [ ] **Step 2: Create `RetrievalUtilityPanel.tsx`**

```tsx
// web/src/components/health/RetrievalUtilityPanel.tsx
import { IndicatorCard } from "./IndicatorCard";
import type { KindredHealth } from "@/lib/backend";

export function RetrievalUtilityPanel({ ru }: { ru: KindredHealth["retrieval_utility"] }) {
  const successPct = (ru.success_rate * 100).toFixed(0);
  const top1Pct = (ru.top1_precision * 100).toFixed(0);
  return (
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-4">
      <IndicatorCard
        label="Total asks"
        value={String(ru.total_asks)}
        hint="All time"
      />
      <IndicatorCard
        label="Outcomes reported"
        value={`${ru.total_outcomes} (${ru.total_asks ? Math.round((ru.total_outcomes / ru.total_asks) * 100) : 0}%)`}
        hint="Reporting coverage"
      />
      <IndicatorCard
        label="Success rate"
        value={`${successPct}%`}
        tone={ru.success_rate >= 0.7 ? "good" : "warn"}
        hint="success + partial"
      />
      <IndicatorCard
        label="Top-1 precision"
        value={`${top1Pct}%`}
        hint={`Mean rank of chosen: ${ru.mean_rank_of_chosen.toFixed(1)}`}
        tone={ru.top1_precision >= 0.5 ? "good" : "warn"}
      />
    </section>
  );
}
```

- [ ] **Step 3: Create `TTFURPanel.tsx`**

```tsx
// web/src/components/health/TTFURPanel.tsx
import { IndicatorCard } from "./IndicatorCard";
import type { KindredHealth } from "@/lib/backend";

function fmt(sec: number | null): string {
  if (sec === null) return "—";
  if (sec < 90) return `${Math.round(sec)}s`;
  if (sec < 3600) return `${Math.round(sec / 60)}m`;
  return `${(sec / 3600).toFixed(1)}h`;
}

export function TTFURPanel({ ttfur }: { ttfur: KindredHealth["ttfur"] }) {
  return (
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <IndicatorCard label="Sample size" value={String(ttfur.sample_size)}
        hint="Agents with at least one success" />
      <IndicatorCard label="TTFUR p50" value={fmt(ttfur.p50_seconds)}
        tone={ttfur.p50_seconds !== null && ttfur.p50_seconds < 60 ? "good" : "warn"} />
      <IndicatorCard label="TTFUR p90" value={fmt(ttfur.p90_seconds)} />
    </section>
  );
}
```

- [ ] **Step 4: Create `TrustLatencyPanel.tsx`**

```tsx
// web/src/components/health/TrustLatencyPanel.tsx
import { IndicatorCard } from "./IndicatorCard";
import type { KindredHealth } from "@/lib/backend";

function fmt(sec: number | null): string {
  if (sec === null) return "—";
  if (sec < 3600) return `${Math.round(sec / 60)}m`;
  if (sec < 86400) return `${(sec / 3600).toFixed(1)}h`;
  return `${(sec / 86400).toFixed(1)}d`;
}

export function TrustLatencyPanel({ tp }: { tp: KindredHealth["trust_propagation"] }) {
  return (
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <IndicatorCard label="Promoted artifacts" value={String(tp.promoted_artifacts)}
        hint="Reached bless threshold" />
      <IndicatorCard label="Propagation p50" value={fmt(tp.p50_seconds)}
        hint="publish → threshold-blessing" />
      <IndicatorCard label="Propagation p90" value={fmt(tp.p90_seconds)} />
    </section>
  );
}
```

- [ ] **Step 5: Create `StalenessPanel.tsx`**

```tsx
// web/src/components/health/StalenessPanel.tsx
import { IndicatorCard } from "./IndicatorCard";
import type { KindredHealth } from "@/lib/backend";

export function StalenessPanel({ sc }: { sc: KindredHealth["staleness_cost"] }) {
  return (
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <IndicatorCard
        label="Shadow hits (7d)"
        value={String(sc.shadow_hits_last_7d)}
        hint="Expired artefacts that would have ranked top-K"
        tone={sc.shadow_hits_last_7d === 0 ? "good" : "warn"}
      />
      <IndicatorCard
        label="Expiring soon (7d)"
        value={String(sc.expiring_soon_hits_last_7d)}
        hint="Asks where returned artifact expires within 7d"
      />
    </section>
  );
}
```

- [ ] **Step 6: Create the page**

```tsx
// web/src/app/dashboard/[slug]/health/page.tsx
import { fetchKindredHealth } from "@/lib/backend";
import { getSessionAgent } from "@/lib/session";
import { RetrievalUtilityPanel } from "@/components/health/RetrievalUtilityPanel";
import { TTFURPanel } from "@/components/health/TTFURPanel";
import { TrustLatencyPanel } from "@/components/health/TrustLatencyPanel";
import { StalenessPanel } from "@/components/health/StalenessPanel";

export default async function HealthPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const session = await getSessionAgent();
  if (!session) {
    return <div className="p-8">Sign in to view health.</div>;
  }
  const h = await fetchKindredHealth(slug, session.agentPubkey);
  return (
    <main className="mx-auto max-w-5xl space-y-8 p-6">
      <header>
        <h1 className="text-2xl font-bold">Network health — {slug}</h1>
        <p className="text-xs text-neutral-500">
          Generated {new Date(h.generated_at).toLocaleString()}
        </p>
      </header>
      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">Retrieval utility</h2>
        <RetrievalUtilityPanel ru={h.retrieval_utility} />
      </div>
      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">Time to first useful retrieval</h2>
        <TTFURPanel ttfur={h.ttfur} />
      </div>
      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">Trust propagation</h2>
        <TrustLatencyPanel tp={h.trust_propagation} />
      </div>
      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">Staleness cost</h2>
        <StalenessPanel sc={h.staleness_cost} />
      </div>
    </main>
  );
}
```

- [ ] **Step 7: Create `loading.tsx`**

```tsx
// web/src/app/dashboard/[slug]/health/loading.tsx
export default function Loading() {
  return <div className="p-6 text-neutral-500">Loading health…</div>;
}
```

- [ ] **Step 8: Smoke-compile**

Run: `cd web && npm run build 2>&1 | tail -30`
Expected: no type errors. If the `getSessionAgent()` signature differs, adapt using the patterns from existing pages (`web/src/app/dashboard/[slug]/audit/page.tsx` is a good reference).

- [ ] **Step 9: Commit**

```bash
git add web/src/app/dashboard/\[slug\]/health web/src/components/health
git commit -m "feat(web): dashboard/[slug]/health — 4 indicator panels"
```

---

### Task 14: Playwright test — health page renders

**Files:**
- Create: `web/tests/health.spec.ts`

- [ ] **Step 1: Write the test**

Create `web/tests/health.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";

test("health page renders all four indicator sections", async ({ page, baseURL }) => {
  // Uses the e2e fixture that signs in a seeded test user with a kindred.
  await page.goto(`${baseURL}/dashboard/claude-code-patterns/health`);

  await expect(page.getByRole("heading", { name: /network health/i })).toBeVisible();
  await expect(page.getByText(/retrieval utility/i)).toBeVisible();
  await expect(page.getByText(/time to first useful retrieval/i)).toBeVisible();
  await expect(page.getByText(/trust propagation/i)).toBeVisible();
  await expect(page.getByText(/staleness cost/i)).toBeVisible();
});
```

- [ ] **Step 2: Run**

Run: `cd web && npx playwright test health.spec.ts`
Expected: PASS (requires the e2e fixture chain from existing dashboard tests — reuse its auth setup).

- [ ] **Step 3: Commit**

```bash
git add web/tests/health.spec.ts
git commit -m "test(web): Playwright coverage for health dashboard"
```

---

## Phase 5 — Benchmark + docs alignment

### Task 15: Rewrite `scripts/onboarding_benchmark.sh` to measure TTFUR

**Files:**
- Modify: `scripts/onboarding_benchmark.sh`

**Why:** Current benchmark measures time-to-install; the first-principles metric is time-to-first-useful-retrieval. The rewrite should: bring up the stack, join, ask a realistic question, report success, and print elapsed wall-clock.

- [ ] **Step 1: Read current script to preserve docker/backend bootstrapping**

Run: `cat scripts/onboarding_benchmark.sh`

- [ ] **Step 2: Replace the measurement block**

Replace the "time the install" section with:

```bash
START_NS=$(date +%s%N)

# 1. Join via invite
INVITE=$(uv run python scripts/mint_invite.py --slug claude-code-patterns)
uv run kin join "$INVITE"

# 2. Ask a realistic query
ASK_JSON=$(uv run kin ask claude-code-patterns "how do I structure commits?" --json || true)
AUDIT_ID=$(python3 -c "import json,sys;print(json.loads(sys.stdin.read())['audit_id'])" <<<"$ASK_JSON")

# 3. Report success (simulating the agent having used the artifact)
uv run kin report "$AUDIT_ID" success --chose "$(python3 -c "import json,sys;print(json.loads(sys.stdin.read())['artifacts'][0]['content_id'])" <<<"$ASK_JSON")"

END_NS=$(date +%s%N)
ELAPSED_MS=$(( (END_NS - START_NS) / 1000000 ))
echo "TTFUR_MS=${ELAPSED_MS}"

# Fail the benchmark if p50 target is missed.
TARGET_MS=60000
if (( ELAPSED_MS > TARGET_MS )); then
    echo "FAIL: TTFUR ${ELAPSED_MS}ms exceeds target ${TARGET_MS}ms"
    exit 1
fi
echo "PASS"
```

Note: this requires `kin ask --json` to exist — if it doesn't, add a `--json` option to `cli/src/kindred_client/commands/ask.py` in a preceding sub-step (dump `resp` via `json.dumps`).

- [ ] **Step 3: Add `--json` option to `kin ask` (prerequisite)**

Modify `cli/src/kindred_client/commands/ask.py` — add a `json_out: bool` option, and when true, `print(json.dumps(resp))` instead of the rich panel.

- [ ] **Step 4: Run benchmark**

Run: `./scripts/onboarding_benchmark.sh`
Expected: `PASS` with `TTFUR_MS < 60000`.

- [ ] **Step 5: Commit**

```bash
git add scripts/onboarding_benchmark.sh cli/src/kindred_client/commands/ask.py
git commit -m "feat(bench): measure TTFUR (join→ask→report success) not just install time"
```

---

### Task 16: Update README + transparency page

**Files:**
- Modify: `README.md`
- Modify: `docs/transparency.md`

- [ ] **Step 1: Add health section to README**

In `README.md`, after the Quick-start block, add:

```markdown
## Network health

Every kindred exposes four first-principles health indicators:

- **Retrieval utility** — success rate, top-1 precision, mean rank of chosen artifact
- **Time to first useful retrieval** — p50/p90 from join → first success
- **Trust propagation** — p50/p90 from publish → threshold-blessing
- **Staleness cost** — shadow hits + expiring-soon returns in the last 7 days

View at `/dashboard/<slug>/health` or fetch `GET /v1/kindreds/<slug>/health`.
```

- [ ] **Step 2: Add section to transparency.md**

Append a section "Network health indicators" to `docs/transparency.md` linking to the endpoint and explaining what each indicator means.

- [ ] **Step 3: Commit**

```bash
git add README.md docs/transparency.md
git commit -m "docs: document the four health indicators + /health endpoint"
```

---

## Self-Review

**Spec coverage check (against the 4 indicators in the first-principles analysis):**
1. Retrieval utility → Tasks 2, 3, 4 (payload enrichment, chosen_content_id, service).
2. TTFUR → Task 5 (service) + Task 15 (benchmark).
3. Trust propagation latency → Task 6 (service), no schema change.
4. Staleness cost → Task 1 (librarian shadow count) + Task 7 (service).

Plus cross-cutting: Task 8 (endpoint), Tasks 9–11 (CLI+plugin auto-report), Tasks 12–14 (web), Task 16 (docs).

**Placeholder scan:** No "TBD" / "appropriate error handling" / etc. — every code step has concrete code. Test helpers (`_seed_*`, `_next_audit_seq`) are defined inline.

**Type consistency:** `KindredHealthResp`, `RetrievalUtility`, `TTFUR`, `TrustPropagation`, `StalenessCost` names are consistent across Pydantic (backend), TypeScript (`web/src/lib/backend.ts`), and component props. `chosen_content_id` is the same field name everywhere (backend schema, service function, CLI option `--chose`, web type).

**Known risks:**
- Task 6 `_seed_blessing` FK to `agents.id` — verify the test DB has FK enforcement relaxed OR seed a real Agent (reuse `backend/tests/helpers.py` if it has an `agent_factory`).
- Task 11 assumes MCP server is Python; if it's a bash wrapper or TS, adapt the "write last_audit_id" step to that language.
- Task 13 `getSessionAgent()` API — may need reshaping to match existing `web/src/lib/session.ts` surface.
- Playwright test (Task 14) needs the standard e2e fixture (auth cookie seeding). If the existing dashboard Playwright tests use a different pattern, match that.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-23-kindred-08-retrieval-utility-network-health.md`. Two execution options:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration. Uses `superpowers:subagent-driven-development`.
2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch with checkpoints.

Which approach?
