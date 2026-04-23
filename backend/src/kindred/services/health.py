"""Compute network-health indicators from audit_log + events + artifacts.

Zero schema changes. Every indicator is a read-only aggregation, safe to call
from a public endpoint because it never exposes agent pubkeys or query text —
only aggregate counts and percentiles.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.schemas.health import RetrievalUtility
from kindred.models.audit import AuditLog
from kindred.models.event import Event


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
