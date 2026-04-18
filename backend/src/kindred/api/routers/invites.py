import base64
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session, require_owner_pubkey
from kindred.api.schemas.invites import InviteOut, IssueInviteReq
from kindred.services.invites import issue_invite
from kindred.services.kindreds import get_kindred_by_slug
from kindred.services.users import get_user_by_pubkey

router = APIRouter()


@router.post("/{slug}/invites", response_model=InviteOut, status_code=201)
async def issue(
    slug: str,
    req: IssueInviteReq,
    session: AsyncSession = Depends(db_session),
    owner_pubkey: bytes = Depends(require_owner_pubkey),
):
    k = await get_kindred_by_slug(session, slug)
    owner = await get_user_by_pubkey(session, owner_pubkey)
    token = secrets.token_urlsafe(32)
    inv = await issue_invite(
        session,
        kindred_id=k.id,
        issued_by=owner.id,
        token=token,
        expires_at=datetime.now(UTC) + timedelta(days=req.expires_in_days),
        issuer_sig=bytes.fromhex(req.issuer_sig),
        issuer_pubkey=owner_pubkey,
        inv_body=base64.b64decode(req.inv_body_b64),
        max_uses=req.max_uses,
    )
    return InviteOut(
        token=inv.token,
        expires_at=inv.expires_at.isoformat(),
        max_uses=inv.max_uses,
        uses=inv.uses,
    )
