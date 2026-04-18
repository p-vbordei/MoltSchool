from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.models.artifact import Artifact, Blessing
from kindred.models.event import Event
from kindred.models.membership import AgentKindredMembership


async def list_events(session: AsyncSession, *, kindred_id: UUID) -> list[Event]:
    q = select(Event).where(Event.kindred_id == kindred_id).order_by(Event.seq)
    return list((await session.execute(q)).scalars())


async def rollback_to(session: AsyncSession, *, kindred_id: UUID, up_to_seq: int) -> None:
    """Revert state changes introduced AFTER `up_to_seq`.
    v0 supports: artifact_uploaded, artifact_blessed, member_joined, member_left.
    """
    events_to_revert = list((await session.execute(
        select(Event).where(Event.kindred_id == kindred_id, Event.seq > up_to_seq)
        .order_by(Event.seq.desc())
    )).scalars())
    for e in events_to_revert:
        if e.event_type == "artifact_uploaded":
            cid = e.payload["content_id"]
            await session.execute(delete(Blessing).where(
                Blessing.artifact_id.in_(select(Artifact.id).where(Artifact.content_id == cid))
            ))
            await session.execute(delete(Artifact).where(Artifact.content_id == cid))
        elif e.event_type == "artifact_blessed":
            cid = e.payload["content_id"]
            signer = bytes.fromhex(e.payload["signer_pubkey"])
            await session.execute(delete(Blessing).where(
                Blessing.signer_pubkey == signer,
                Blessing.artifact_id.in_(select(Artifact.id).where(Artifact.content_id == cid)),
            ))
        elif e.event_type == "member_joined":
            pk = bytes.fromhex(e.payload["agent_pubkey"])
            from kindred.models.agent import Agent
            await session.execute(delete(AgentKindredMembership).where(
                AgentKindredMembership.kindred_id == kindred_id,
                AgentKindredMembership.agent_id.in_(select(Agent.id).where(Agent.pubkey == pk)),
            ))
        elif e.event_type == "member_left":
            # idempotent: do nothing on replay
            pass
        await session.execute(delete(Event).where(Event.id == e.id))
    await session.flush()
