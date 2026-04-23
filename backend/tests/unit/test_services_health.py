"""Unit tests for kindred.services.health — each indicator in isolation."""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func, select

from kindred.services.health import compute_retrieval_utility, compute_ttfur
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


async def _seed_agent_with_join_and_success(db_session, kindred, *, join_at, success_at):
    """Create a User+Agent+Membership+Ask+Outcome chain with controlled timestamps."""
    from datetime import UTC, datetime
    from kindred.models.agent import Agent
    from kindred.models.audit import AuditLog
    from kindred.models.event import Event
    from kindred.models.membership import AgentKindredMembership
    from kindred.models.user import User

    suffix = uuid4().hex[:16]
    u = User(email=f"ttfur-{suffix}@x", display_name=f"u-{suffix}", pubkey=uuid4().bytes * 2)
    db_session.add(u)
    await db_session.flush()

    ag_pk = uuid4().bytes * 2  # 32 bytes, guaranteed unique per call
    agent = Agent(
        owner_id=u.id,
        pubkey=ag_pk,
        display_name=f"agent-{suffix}",
        attestation_sig=b"x" * 64,
        attestation_scope="{}",
        attestation_expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    db_session.add(agent)
    await db_session.flush()

    membership = AgentKindredMembership(
        agent_id=agent.id,
        kindred_id=kindred.id,
        invite_sig=b"x" * 64,
        accept_sig=b"x" * 64,
    )
    membership.created_at = join_at
    db_session.add(membership)
    await db_session.flush()

    audit = AuditLog(
        kindred_id=kindred.id,
        agent_pubkey=ag_pk,
        action="ask",
        payload={
            "query": "q", "artifact_ids_returned": ["X"], "scores": [1.0],
            "tiers": ["peer-shared"], "k": 1, "expired_shadow_hits": 0,
            "blocked_injection": False,
        },
        facilitator_sig=b"x" * 64,
        seq=await _next_audit_seq(db_session, kindred.id),
    )
    audit.created_at = success_at
    db_session.add(audit)
    await db_session.flush()

    evt = Event(
        kindred_id=kindred.id,
        seq=await _next_event_seq(db_session, kindred.id),
        event_type="outcome_reported",
        payload={
            "audit_id": str(audit.id), "result": "success", "notes": "",
            "artifact_ids": ["X"], "chosen_content_id": "X", "rank_of_chosen": 0,
        },
    )
    evt.created_at = success_at
    db_session.add(evt)
    await db_session.flush()
    return membership


async def _seed_agent_join_only(db_session, kindred, *, join_at):
    """Agent joins but never reports a success — should be excluded from TTFUR sample."""
    from datetime import UTC, datetime
    from kindred.models.agent import Agent
    from kindred.models.membership import AgentKindredMembership
    from kindred.models.user import User

    suffix = uuid4().hex[:16]
    u = User(email=f"join-only-{suffix}@x", display_name=f"u-{suffix}", pubkey=uuid4().bytes * 2)
    db_session.add(u)
    await db_session.flush()

    agent = Agent(
        owner_id=u.id,
        pubkey=uuid4().bytes * 2,
        display_name=f"agent-{suffix}",
        attestation_sig=b"x" * 64,
        attestation_scope="{}",
        attestation_expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    db_session.add(agent)
    await db_session.flush()

    membership = AgentKindredMembership(
        agent_id=agent.id, kindred_id=kindred.id,
        invite_sig=b"x" * 64, accept_sig=b"x" * 64,
    )
    membership.created_at = join_at
    db_session.add(membership)
    await db_session.flush()
    return membership


async def test_ttfur_measures_join_to_first_success(db_session):
    """TTFUR = first success timestamp − agent membership created_at, per agent
    that has both. Report p50/p90 over the sample of agents with successes."""
    from datetime import UTC, datetime, timedelta
    setup = await make_full_setup(db_session, slug="ttfur-test")
    kindred = setup["kindred"]
    now = datetime.now(UTC)
    # Agent A: joined 10 min ago, first success 30s after join
    await _seed_agent_with_join_and_success(
        db_session, kindred,
        join_at=now - timedelta(minutes=10),
        success_at=now - timedelta(minutes=10) + timedelta(seconds=30),
    )
    # Agent B: joined 20 min ago, first success 90s after join
    await _seed_agent_with_join_and_success(
        db_session, kindred,
        join_at=now - timedelta(minutes=20),
        success_at=now - timedelta(minutes=20) + timedelta(seconds=90),
    )
    # Agent C: joined just now, no success yet — excluded from percentile.
    await _seed_agent_join_only(db_session, kindred, join_at=now)

    result = await compute_ttfur(db_session, kindred_id=kindred.id)
    assert result.sample_size == 2
    # p50 over [30.0, 90.0] with nearest-rank picker — accept either endpoint.
    assert result.p50_seconds is not None
    assert 25.0 <= result.p50_seconds <= 95.0
    assert result.p90_seconds is not None
