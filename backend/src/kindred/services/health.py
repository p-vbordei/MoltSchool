"""Compute network-health indicators from audit_log + events + artifacts.

Zero schema changes. Every indicator is a read-only aggregation, safe to call
from a public endpoint because it never exposes agent pubkeys or query text —
only aggregate counts and percentiles.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.schemas.health import RetrievalUtility, TTFUR, TrustPropagation
from kindred.facilitator.outcomes import SUCCESS_RESULTS
from kindred.models.agent import Agent
from kindred.models.artifact import Artifact, Blessing
from kindred.models.audit import AuditLog
from kindred.models.event import Event
from kindred.models.membership import AgentKindredMembership


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round(q * (len(ordered) - 1)))))
    return ordered[idx]


def _as_utc(dt: datetime) -> datetime:
    """Coerce a possibly tz-naive datetime to UTC.

    SQLAlchemy+SQLite drops tzinfo from ``DateTime(timezone=True)`` columns;
    Postgres preserves it. This helper lets us subtract naive and aware
    datetimes without a TypeError in tests.
    """
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


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

    successes = [o for o in outcomes if o.payload.get("result") in SUCCESS_RESULTS]
    ranks = [o.payload["rank_of_chosen"] for o in successes
             if o.payload.get("rank_of_chosen") is not None]

    return RetrievalUtility(
        total_asks=total_asks,
        total_outcomes=len(outcomes),
        success_rate=(len(successes) / len(outcomes)) if outcomes else 0.0,
        mean_rank_of_chosen=(sum(ranks) / len(ranks)) if ranks else 0.0,
        top1_precision=(sum(1 for r in ranks if r == 0) / len(ranks)) if ranks else 0.0,
    )


async def compute_ttfur(
    session: AsyncSession, *, kindred_id: UUID,
) -> TTFUR:
    """Time from agent joining the kindred until their first success outcome.

    Joined = AgentKindredMembership.created_at. First success = earliest
    ``outcome_reported`` event with result in SUCCESS_RESULTS whose ``audit_id``
    references an /ask audit performed by that agent's pubkey.
    """
    members_q = (
        select(AgentKindredMembership, Agent.pubkey)
        .join(Agent, AgentKindredMembership.agent_id == Agent.id)
        .where(AgentKindredMembership.kindred_id == kindred_id)
    )
    member_rows = (await session.execute(members_q)).all()

    # Fetch outcome_reported events once, ordered asc, to find the first-success per agent.
    outcome_events = list((await session.execute(
        select(Event).where(
            Event.kindred_id == kindred_id,
            Event.event_type == "outcome_reported",
        ).order_by(Event.created_at.asc())
    )).scalars())

    deltas_seconds: list[float] = []
    for membership, agent_pubkey in member_rows:
        agent_asks = list((await session.execute(
            select(AuditLog.id).where(
                AuditLog.kindred_id == kindred_id,
                AuditLog.agent_pubkey == agent_pubkey,
                AuditLog.action == "ask",
            )
        )).scalars())
        if not agent_asks:
            continue
        ask_ids = {str(aid) for aid in agent_asks}

        first_success_at: datetime | None = None
        for e in outcome_events:
            if (e.payload.get("result") in SUCCESS_RESULTS
                    and e.payload.get("audit_id") in ask_ids):
                first_success_at = e.created_at
                break
        if first_success_at is None:
            continue

        delta = (_as_utc(first_success_at) - _as_utc(membership.created_at)).total_seconds()
        if delta >= 0:
            deltas_seconds.append(delta)

    return TTFUR(
        sample_size=len(deltas_seconds),
        p50_seconds=_percentile(deltas_seconds, 0.5),
        p90_seconds=_percentile(deltas_seconds, 0.9),
    )


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
        delta = (_as_utc(nth.created_at) - _as_utc(art.created_at)).total_seconds()
        if delta >= 0:
            deltas.append(delta)

    return TrustPropagation(
        promoted_artifacts=len(deltas),
        p50_seconds=_percentile(deltas, 0.5),
        p90_seconds=_percentile(deltas, 0.9),
    )
