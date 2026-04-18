from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.crypto.canonical import canonical_json
from kindred.crypto.keys import sign
from kindred.models.audit import AuditLog
from kindred.models.event import Event

_MAX_SEQ_RETRIES = 3


async def _next_seq(session: AsyncSession, kindred_id: UUID, table) -> int:
    # `SELECT max(seq)+1` is inherently racy under concurrent writers.
    # The (kindred_id, seq) UNIQUE constraint on AuditLog/Event catches
    # collisions with IntegrityError on flush; append_audit / append_event
    # wrap their insert in a SAVEPOINT and retry on collision.
    q = select(func.coalesce(func.max(table.seq), 0) + 1).where(
        table.kindred_id == kindred_id
    )
    return (await session.execute(q)).scalar_one()


async def _flush_with_seq_retry(
    session: AsyncSession,
    kindred_id: UUID,
    table,
    build_entry,
    max_attempts: int = _MAX_SEQ_RETRIES,
):
    """Compute seq, add entry, flush inside a SAVEPOINT; retry on IntegrityError.

    ``build_entry(seq)`` must return a fresh ORM instance each call — retries
    cannot reuse an expunged/rolled-back object.
    """
    last_error: IntegrityError | None = None
    for _attempt in range(max_attempts):
        seq = await _next_seq(session, kindred_id, table)
        entry = build_entry(seq)
        sp = await session.begin_nested()  # SAVEPOINT
        session.add(entry)
        try:
            await session.flush()
            await sp.commit()  # release SAVEPOINT
            return entry
        except IntegrityError as e:
            last_error = e
            await sp.rollback()  # rollback only this insert
            # entry is now detached from this session; next iteration builds fresh
            continue
    assert last_error is not None
    raise last_error


async def append_audit(
    session: AsyncSession,
    *,
    kindred_id: UUID,
    agent_pubkey: bytes,
    action: str,
    payload: dict,
    facilitator_sk: bytes,
) -> AuditLog:
    def build(seq: int) -> AuditLog:
        body = canonical_json(
            {
                "kindred_id": str(kindred_id),
                "seq": seq,
                "action": action,
                "payload": payload,
            }
        )
        sig = sign(facilitator_sk, body)
        return AuditLog(
            kindred_id=kindred_id,
            agent_pubkey=agent_pubkey,
            action=action,
            payload=payload,
            facilitator_sig=sig,
            seq=seq,
        )

    return await _flush_with_seq_retry(session, kindred_id, AuditLog, build)


async def append_event(
    session: AsyncSession, *, kindred_id: UUID, event_type: str, payload: dict
) -> Event:
    def build(seq: int) -> Event:
        return Event(
            kindred_id=kindred_id, seq=seq, event_type=event_type, payload=payload
        )

    return await _flush_with_seq_retry(session, kindred_id, Event, build)
