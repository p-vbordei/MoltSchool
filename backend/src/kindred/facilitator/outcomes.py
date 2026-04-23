"""Outcome telemetry — agents report how useful returned artefacts were.

Success/partial → artifact.outcome_successes +=1; fail/overridden → uses only.
Feeds future match-making / corpus health metrics. Zero LLM use.
"""
from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.errors import NotFoundError, ValidationError
from kindred.models.artifact import Artifact
from kindred.models.audit import AuditLog
from kindred.services.audit import append_event


class OutcomeResult(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAIL = "fail"
    OVERRIDDEN = "overridden"


SUCCESS_RESULTS: frozenset[str] = frozenset({OutcomeResult.SUCCESS.value, OutcomeResult.PARTIAL.value})


async def report_outcome(
    session: AsyncSession, *, audit_id: UUID, result: str | OutcomeResult,
    notes: str = "", chosen_content_id: str | None = None,
) -> None:
    """Credit each returned artifact for an earlier /ask call.

    Looks up the audit entry, walks its `artifact_ids_returned`, and bumps
    `outcome_uses` (+successes on SUCCESS/PARTIAL). Emits an `outcome_reported`
    event on the kindred timeline.
    """
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

    if chosen_content_id is not None and chosen_content_id not in cids:
        raise ValidationError(
            f"chosen_content_id {chosen_content_id!r} was not in audit's returned set"
        )

    is_success = parsed.value in SUCCESS_RESULTS
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
