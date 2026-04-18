from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.crypto.keys import verify
from kindred.errors import NotFoundError, SignatureError, ValidationError
from kindred.models.invite import Invite


async def issue_invite(
    session: AsyncSession,
    *,
    kindred_id: UUID,
    issued_by: UUID,
    token: str,
    expires_at: datetime,
    issuer_sig: bytes,
    issuer_pubkey: bytes,
    inv_body: bytes,
    max_uses: int = 1,
) -> Invite:
    if not verify(issuer_pubkey, inv_body, issuer_sig):
        raise SignatureError("invalid issuer signature on invite body")
    if len(token) < 16:
        raise ValidationError("token too short")
    inv = Invite(
        kindred_id=kindred_id,
        issued_by=issued_by,
        token=token,
        expires_at=expires_at,
        max_uses=max_uses,
        uses=0,
        issuer_sig=issuer_sig,
    )
    session.add(inv)
    await session.flush()
    return inv


async def get_invite_by_token(session: AsyncSession, token: str) -> Invite:
    inv = (
        await session.execute(select(Invite).where(Invite.token == token))
    ).scalar_one_or_none()
    if not inv:
        raise NotFoundError("invite not found")
    return inv


async def revoke_invite(session: AsyncSession, token: str) -> None:
    inv = await get_invite_by_token(session, token)
    inv.revoked = True
    await session.flush()


def assert_invite_usable(inv: Invite) -> None:
    if inv.revoked:
        raise ValidationError("invite revoked")
    # Normalize: sqlite+aiosqlite may return naive datetimes for DateTime(timezone=True)
    exp = (
        inv.expires_at
        if inv.expires_at.tzinfo
        else inv.expires_at.replace(tzinfo=UTC)
    )
    if exp < datetime.now(UTC):
        raise ValidationError("invite expired")
    if inv.uses >= inv.max_uses:
        raise ValidationError("invite exhausted")
