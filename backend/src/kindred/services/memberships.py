from sqlalchemy.ext.asyncio import AsyncSession

from kindred.crypto.keys import verify
from kindred.errors import SignatureError
from kindred.models.membership import AgentKindredMembership
from kindred.services.agents import get_agent_by_pubkey
from kindred.services.audit import append_event
from kindred.services.invites import assert_invite_usable, get_invite_by_token


async def join_kindred(
    session: AsyncSession,
    *,
    token: str,
    agent_pubkey: bytes,
    accept_sig: bytes,
    accept_body: bytes,
) -> AgentKindredMembership:
    inv = await get_invite_by_token(session, token)
    assert_invite_usable(inv)
    if not verify(agent_pubkey, accept_body, accept_sig):
        raise SignatureError("invalid accept signature")
    agent = await get_agent_by_pubkey(session, agent_pubkey)
    m = AgentKindredMembership(
        agent_id=agent.id,
        kindred_id=inv.kindred_id,
        invite_sig=inv.issuer_sig,
        accept_sig=accept_sig,
    )
    session.add(m)
    inv.uses += 1
    await session.flush()
    await append_event(
        session,
        kindred_id=inv.kindred_id,
        event_type="member_joined",
        payload={"agent_pubkey": agent_pubkey.hex()},
    )
    return m


async def leave_kindred(
    session: AsyncSession, *, agent_pubkey: bytes, kindred_slug: str
) -> None:
    from sqlalchemy import delete

    from kindred.services.kindreds import get_kindred_by_slug

    k = await get_kindred_by_slug(session, kindred_slug)
    agent = await get_agent_by_pubkey(session, agent_pubkey)
    q = delete(AgentKindredMembership).where(
        AgentKindredMembership.agent_id == agent.id,
        AgentKindredMembership.kindred_id == k.id,
    )
    await session.execute(q)
    await append_event(
        session,
        kindred_id=k.id,
        event_type="member_left",
        payload={"agent_pubkey": agent_pubkey.hex()},
    )
