import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.crypto.canonical import canonical_json
from kindred.crypto.keys import pubkey_to_str, verify
from kindred.errors import NotFoundError, SignatureError
from kindred.models.agent import Agent
from kindred.services.users import get_user


async def register_agent(
    session: AsyncSession,
    *,
    owner_id: UUID,
    agent_pubkey: bytes,
    display_name: str,
    scope: dict,
    expires_at: datetime,
    sig: bytes,
) -> Agent:
    owner = await get_user(session, owner_id)
    payload = canonical_json(
        {
            "agent_pubkey": pubkey_to_str(agent_pubkey),
            "scope": scope,
            "expires_at": expires_at.isoformat(),
        }
    )
    if not verify(owner.pubkey, payload, sig):
        raise SignatureError("invalid owner attestation signature")
    a = Agent(
        owner_id=owner_id,
        pubkey=agent_pubkey,
        display_name=display_name,
        attestation_sig=sig,
        attestation_scope=json.dumps(scope),
        attestation_expires_at=expires_at,
    )
    session.add(a)
    await session.flush()
    return a


async def get_agent_by_pubkey(session: AsyncSession, pubkey: bytes) -> Agent:
    a = (
        await session.execute(select(Agent).where(Agent.pubkey == pubkey))
    ).scalar_one_or_none()
    if not a:
        raise NotFoundError("agent not found by pubkey")
    return a
