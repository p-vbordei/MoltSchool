from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from kindred.models.artifact import Artifact, Blessing
from kindred.crypto.keys import verify
from kindred.errors import SignatureError, ConflictError
from kindred.services.audit import append_event


async def add_blessing(
    session: AsyncSession, *, artifact: Artifact, signer_agent_id: UUID,
    signer_pubkey: bytes, sig: bytes,
) -> Blessing:
    if not verify(signer_pubkey, artifact.content_id.encode(), sig):
        raise SignatureError("invalid blessing signature over content_id")
    exists = (await session.execute(
        select(Blessing).where(
            Blessing.artifact_id == artifact.id,
            Blessing.signer_pubkey == signer_pubkey,
        )
    )).scalar_one_or_none()
    if exists:
        raise ConflictError("already blessed by this signer")
    b = Blessing(
        artifact_id=artifact.id, signer_pubkey=signer_pubkey,
        signer_agent_id=signer_agent_id, sig=sig,
    )
    session.add(b)
    await session.flush()
    await append_event(session, kindred_id=artifact.kindred_id, event_type="artifact_blessed",
                       payload={"content_id": artifact.content_id,
                                "signer_pubkey": signer_pubkey.hex()})
    return b


async def count_blessings(session: AsyncSession, artifact_id: UUID) -> int:
    q = select(func.count()).select_from(Blessing).where(Blessing.artifact_id == artifact_id)
    return (await session.execute(q)).scalar_one()


async def compute_tier(session: AsyncSession, *, artifact: Artifact, threshold: int) -> str:
    n = await count_blessings(session, artifact.id)
    return "class-blessed" if n >= threshold else "peer-shared"
