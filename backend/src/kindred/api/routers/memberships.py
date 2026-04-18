import base64

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session
from kindred.api.schemas.invites import JoinReq
from kindred.crypto.keys import str_to_pubkey
from kindred.services.memberships import join_kindred

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
