from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session, require_owner_pubkey
from kindred.api.schemas.kindreds import CreateKindredReq, InstallOut, KindredOut
from kindred.services.kindreds import (
    create_kindred,
    get_kindred_by_slug,
    mint_public_install_invite,
)
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
        is_public=req.is_public,
    )
    return KindredOut.from_model(k)


@router.get("/{slug}", response_model=KindredOut)
async def get(slug: str, session: AsyncSession = Depends(db_session)):
    return KindredOut.from_model(await get_kindred_by_slug(session, slug))


@router.post("/{slug}/install", response_model=InstallOut)
async def install(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(db_session),
):
    """Mint a one-time install invite for a public kindred.

    Private kindreds return 403 — they require an owner-issued invite via
    the normal POST /v1/kindreds/{slug}/invites flow.
    """
    k = await get_kindred_by_slug(session, slug)
    if not k.is_public:
        raise HTTPException(status_code=403, detail="kindred is not public")
    inv = await mint_public_install_invite(session, kindred=k)
    base = str(request.base_url).rstrip("/")
    # Web-landing URL shape: /k/<slug>?inv=<token>.
    invite_url = f"{base}/k/{slug}?inv={inv.token}"
    return InstallOut(invite_url=invite_url, expires_at=inv.expires_at.isoformat())
