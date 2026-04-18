from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.errors import ConflictError, NotFoundError
from kindred.models.user import User


async def register_user(
    session: AsyncSession, *, email: str, display_name: str, pubkey: bytes
) -> User:
    exists = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if exists:
        raise ConflictError(f"email already registered: {email}")
    u = User(email=email, display_name=display_name, pubkey=pubkey)
    session.add(u)
    await session.flush()
    return u


async def get_user(session: AsyncSession, user_id: UUID) -> User:
    u = (
        await session.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not u:
        raise NotFoundError(f"user not found: {user_id}")
    return u


async def get_user_by_pubkey(session: AsyncSession, pubkey: bytes) -> User:
    u = (
        await session.execute(select(User).where(User.pubkey == pubkey))
    ).scalar_one_or_none()
    if not u:
        raise NotFoundError("user not found by pubkey")
    return u
