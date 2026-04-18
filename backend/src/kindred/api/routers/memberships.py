import base64

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session
from kindred.api.schemas.invites import JoinReq
from kindred.crypto.keys import str_to_pubkey
from kindred.services.memberships import join_kindred, leave_kindred

router = APIRouter()


@router.post("/join", status_code=201)
async def join(req: JoinReq, session: AsyncSession = Depends(db_session)):
    m = await join_kindred(
        session,
        token=req.token,
        agent_pubkey=str_to_pubkey(req.agent_pubkey),
        accept_sig=bytes.fromhex(req.accept_sig),
        accept_body=base64.b64decode(req.accept_body_b64),
    )
    return {"membership_id": str(m.id), "kindred_id": str(m.kindred_id)}


async def _parse_agent_pubkey(x_agent_pubkey: str = Header(...)) -> bytes:
    try:
        return str_to_pubkey(x_agent_pubkey)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.post("/kindreds/{slug}/leave", status_code=200)
async def leave(
    slug: str,
    session: AsyncSession = Depends(db_session),
    agent_pubkey: bytes = Depends(_parse_agent_pubkey),
):
    await leave_kindred(session, agent_pubkey=agent_pubkey, kindred_slug=slug)
    return {"ok": True}
