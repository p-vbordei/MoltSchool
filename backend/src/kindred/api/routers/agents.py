from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session
from kindred.api.schemas.agents import AgentOut, RegisterAgentReq
from kindred.crypto.keys import pubkey_to_str, str_to_pubkey
from kindred.services.agents import register_agent

router = APIRouter()


@router.post("/{user_id}/agents", response_model=AgentOut, status_code=201)
async def create(
    user_id: UUID,
    req: RegisterAgentReq,
    session: AsyncSession = Depends(db_session),
):
    a = await register_agent(
        session,
        owner_id=user_id,
        agent_pubkey=str_to_pubkey(req.agent_pubkey),
        display_name=req.display_name,
        scope=req.scope,
        expires_at=datetime.fromisoformat(req.expires_at),
        sig=bytes.fromhex(req.sig),
    )
    return AgentOut(
        id=str(a.id),
        owner_id=str(a.owner_id),
        pubkey=pubkey_to_str(a.pubkey),
        display_name=a.display_name,
    )
