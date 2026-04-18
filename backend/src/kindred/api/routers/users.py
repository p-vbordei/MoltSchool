from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session
from kindred.api.schemas.users import RegisterUserReq, UserOut
from kindred.crypto.keys import pubkey_to_str, str_to_pubkey
from kindred.services.users import get_user_by_pubkey, register_user

router = APIRouter()


@router.post("", response_model=UserOut, status_code=201)
async def create(req: RegisterUserReq, session: AsyncSession = Depends(db_session)):
    u = await register_user(
        session,
        email=req.email,
        display_name=req.display_name,
        pubkey=str_to_pubkey(req.pubkey),
    )
    return UserOut(
        id=str(u.id),
        email=u.email,
        display_name=u.display_name,
        pubkey=pubkey_to_str(u.pubkey),
    )


@router.get("/by-pubkey/{pubkey}", response_model=UserOut)
async def get_by_pk(pubkey: str, session: AsyncSession = Depends(db_session)):
    u = await get_user_by_pubkey(session, str_to_pubkey(pubkey))
    return UserOut(
        id=str(u.id),
        email=u.email,
        display_name=u.display_name,
        pubkey=pubkey_to_str(u.pubkey),
    )
