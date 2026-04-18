from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.crypto.canonical import canonical_json
from kindred.crypto.keys import sign
from kindred.models.audit import AuditLog
from kindred.models.event import Event


async def _next_seq(session: AsyncSession, kindred_id: UUID, table) -> int:
    # NOTE: `SELECT max(seq)+1` is inherently racy under concurrent writers.
    # The (kindred_id, seq) UNIQUE constraint on AuditLog/Event makes collisions
    # fail LOUDLY with IntegrityError on flush rather than silently corrupt.
    # TODO: add bounded retry-on-IntegrityError in append_audit/append_event for
    # production-quality behavior under contention.
    q = select(func.coalesce(func.max(table.seq), 0) + 1).where(
        table.kindred_id == kindred_id
    )
    return (await session.execute(q)).scalar_one()


async def append_audit(
    session: AsyncSession,
    *,
    kindred_id: UUID,
    agent_pubkey: bytes,
    action: str,
    payload: dict,
    facilitator_sk: bytes,
) -> AuditLog:
    seq = await _next_seq(session, kindred_id, AuditLog)
    body = canonical_json(
        {
            "kindred_id": str(kindred_id),
            "seq": seq,
            "action": action,
            "payload": payload,
        }
    )
    sig = sign(facilitator_sk, body)
    entry = AuditLog(
        kindred_id=kindred_id,
        agent_pubkey=agent_pubkey,
        action=action,
        payload=payload,
        facilitator_sig=sig,
        seq=seq,
    )
    session.add(entry)
    await session.flush()
    return entry


async def append_event(
    session: AsyncSession, *, kindred_id: UUID, event_type: str, payload: dict
) -> Event:
    seq = await _next_seq(session, kindred_id, Event)
    e = Event(
        kindred_id=kindred_id, seq=seq, event_type=event_type, payload=payload
    )
    session.add(e)
    await session.flush()
    return e
