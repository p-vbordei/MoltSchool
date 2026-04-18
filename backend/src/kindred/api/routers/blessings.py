from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session
from kindred.api.schemas.blessings import AddBlessingReq
from kindred.crypto.keys import str_to_pubkey
from kindred.services.agents import get_agent_by_pubkey
from kindred.services.artifacts import get_artifact
from kindred.services.blessings import add_blessing

router = APIRouter()


@router.post("/{slug}/artifacts/{content_id:path}/bless", status_code=201)
async def bless(
    slug: str,
    content_id: str,
    req: AddBlessingReq,
    session: AsyncSession = Depends(db_session),
):
    art = await get_artifact(session, content_id)
    signer_pk = str_to_pubkey(req.signer_pubkey)
    agent = await get_agent_by_pubkey(session, signer_pk)
    b = await add_blessing(
        session,
        artifact=art,
        signer_agent_id=agent.id,
        signer_pubkey=signer_pk,
        sig=bytes.fromhex(req.sig),
    )
    return {"blessing_id": str(b.id)}
