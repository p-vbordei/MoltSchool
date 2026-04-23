import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.errors import ConflictError, NotFoundError, ValidationError
from kindred.models.agent import Agent
from kindred.models.kindred import Kindred
from kindred.models.membership import AgentKindredMembership
from kindred.services.audit import append_event

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,63}$")

# Reserved to prevent day-one impersonation of first-party or trust-authority
# identities. Checked as exact match and as prefix for namespaced squatting
# (e.g. `anthropic-evil` is blocked because it starts with `anthropic-`).
RESERVED_SLUGS = frozenset(
    {
        "kindred",
        "kindred-official",
        "kindred-admin",
        "kindred-security",
        "official",
        "admin",
        "root",
        "system",
        "security",
        "anthropic",
        "sigstore",
    }
)
RESERVED_PREFIXES = ("kindred-", "anthropic-", "sigstore-", "official-")


def _is_reserved(slug: str) -> bool:
    if slug in RESERVED_SLUGS:
        return True
    return any(slug.startswith(p) for p in RESERVED_PREFIXES)


async def create_kindred(
    session: AsyncSession,
    *,
    owner_id: UUID,
    slug: str,
    display_name: str,
    description: str = "",
    bless_threshold: int = 2,
) -> Kindred:
    if not SLUG_RE.match(slug):
        raise ValidationError(f"invalid slug: {slug!r}")
    if _is_reserved(slug):
        raise ValidationError(f"reserved slug: {slug!r}")
    exists = (
        await session.execute(select(Kindred).where(Kindred.slug == slug))
    ).scalar_one_or_none()
    if exists:
        raise ConflictError(f"slug exists: {slug}")
    k = Kindred(
        slug=slug,
        display_name=display_name,
        description=description,
        created_by=owner_id,
        bless_threshold=bless_threshold,
    )
    session.add(k)
    await session.flush()
    await append_event(
        session,
        kindred_id=k.id,
        event_type="kindred_created",
        payload={"slug": slug, "owner": str(owner_id)},
    )
    return k


async def get_kindred_by_slug(session: AsyncSession, slug: str) -> Kindred:
    k = (
        await session.execute(select(Kindred).where(Kindred.slug == slug))
    ).scalar_one_or_none()
    if not k:
        raise NotFoundError(f"kindred not found: {slug}")
    return k


async def list_user_kindreds(
    session: AsyncSession, user_id: UUID
) -> list[Kindred]:
    q = (
        select(Kindred)
        .join(
            AgentKindredMembership,
            AgentKindredMembership.kindred_id == Kindred.id,
        )
        .join(Agent, Agent.id == AgentKindredMembership.agent_id)
        .where(Agent.owner_id == user_id)
        .distinct()
    )
    return list((await session.execute(q)).scalars())
