from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session, require_owner_pubkey
from kindred.services.kindreds import get_kindred_by_slug
from kindred.services.rollback import rollback_to

router = APIRouter()


class RollbackReq(BaseModel):
    up_to_seq: int


@router.post("/{slug}/rollback", status_code=200)
async def rollback(
    slug: str,
    req: RollbackReq,
    session: AsyncSession = Depends(db_session),
    _: bytes = Depends(require_owner_pubkey),
):
    k = await get_kindred_by_slug(session, slug)
    await rollback_to(session, kindred_id=k.id, up_to_seq=req.up_to_seq)
    return {"rolled_back_to": req.up_to_seq}
