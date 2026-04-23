"""Unit tests for kindred.services.health — each indicator in isolation."""
from __future__ import annotations

import pytest
from sqlalchemy import func, select

from kindred.services.health import compute_retrieval_utility
from tests.helpers import make_full_setup


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


async def _seed_ask_with_outcome(db_session, kindred, ag_pk, cids, *, chosen, result):
    """Creates a ask audit with given returned cids, then an outcome_reported event."""
    from kindred.models.audit import AuditLog
    from kindred.models.event import Event
    audit = AuditLog(
        kindred_id=kindred.id, agent_pubkey=ag_pk, action="ask",
        payload={"query": "q", "artifact_ids_returned": cids, "scores": [1.0]*len(cids),
                 "tiers": ["peer-shared"]*len(cids), "k": len(cids),
                 "expired_shadow_hits": 0, "blocked_injection": False},
        facilitator_sig=b"x"*64, seq=await _next_audit_seq(db_session, kindred.id),
    )
    db_session.add(audit)
    await db_session.flush()
    evt = Event(
        kindred_id=kindred.id,
        seq=await _next_event_seq(db_session, kindred.id),
        event_type="outcome_reported",
        payload={"audit_id": str(audit.id), "result": result, "notes": "",
                 "artifact_ids": cids, "chosen_content_id": chosen,
                 "rank_of_chosen": cids.index(chosen)},
    )
    db_session.add(evt)
    await db_session.flush()
    return audit


async def _seed_ask_without_outcome(db_session, kindred, ag_pk, cids):
    from kindred.models.audit import AuditLog
    audit = AuditLog(
        kindred_id=kindred.id, agent_pubkey=ag_pk, action="ask",
        payload={"query": "q", "artifact_ids_returned": cids, "scores": [1.0]*len(cids),
                 "tiers": ["peer-shared"]*len(cids), "k": len(cids),
                 "expired_shadow_hits": 0, "blocked_injection": False},
        facilitator_sig=b"x"*64, seq=await _next_audit_seq(db_session, kindred.id),
    )
    db_session.add(audit)
    await db_session.flush()
    return audit


@pytest.mark.asyncio
async def test_retrieval_utility_success_rate_and_mrr(db_session):
    """Computes: total_asks, total_outcomes, success_rate, mean_rank_of_chosen."""
    setup = await make_full_setup(db_session, slug="rt-util")
    kindred = setup["kindred"]
    ag_pk = setup["ag_pk"]

    # Seed 3 asks; 2 outcomes reported (1 success @ rank 0, 1 success @ rank 2).
    await _seed_ask_with_outcome(db_session, kindred, ag_pk, ["X", "Y", "Z"],
                                 chosen="X", result="success")
    await _seed_ask_with_outcome(db_session, kindred, ag_pk, ["A", "B", "C"],
                                 chosen="C", result="success")
    await _seed_ask_without_outcome(db_session, kindred, ag_pk, ["P", "Q"])

    result = await compute_retrieval_utility(db_session, kindred_id=kindred.id)
    assert result.total_asks == 3
    assert result.total_outcomes == 2
    assert result.success_rate == 1.0        # both outcomes succeeded
    assert result.mean_rank_of_chosen == 1.0 # mean(0, 2)
    assert result.top1_precision == 0.5      # 1 of 2 outcomes chose rank 0
