from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session, require_owner_pubkey
from kindred.api.schemas.kindreds import CreateKindredReq, KindredOut
from kindred.services.kindreds import create_kindred, get_kindred_by_slug
from kindred.services.users import get_user_by_pubkey

router = APIRouter()


@router.post("", response_model=KindredOut, status_code=201)
async def create(
    req: CreateKindredReq,
    session: AsyncSession = Depends(db_session),
    owner_pubkey: bytes = Depends(require_owner_pubkey),
):
    owner = await get_user_by_pubkey(session, owner_pubkey)
    k = await create_kindred(
        session,
        owner_id=owner.id,
        slug=req.slug,
        display_name=req.display_name,
        description=req.description,
        bless_threshold=req.bless_threshold,
    )
    return KindredOut.from_model(k)


@router.get("/{slug}", response_model=KindredOut)
async def get(slug: str, session: AsyncSession = Depends(db_session)):
    return KindredOut.from_model(await get_kindred_by_slug(session, slug))
