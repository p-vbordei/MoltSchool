import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import get_settings
from kindred.crypto.canonical import canonical_json
from kindred.crypto.keys import sign
from kindred.errors import ConflictError, NotFoundError, ValidationError
from kindred.models.agent import Agent
from kindred.models.invite import Invite
from kindred.models.kindred import Kindred
from kindred.models.membership import AgentKindredMembership
from kindred.services.audit import append_event

PUBLIC_INSTALL_INVITE_TTL_MINUTES = 15

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
    is_public: bool = False,
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
        is_public=is_public,
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


async def mint_public_install_invite(
    session: AsyncSession,
    *,
    kindred: Kindred,
) -> Invite:
    """Server-mint a short-lived, single-use invite for a public kindred.

    Attributed to the kindred's owner (created_by) so the audit trail stays
    coherent. The facilitator key signs the canonical invite body — this
    lets auditors tell server-minted public invites apart from
    owner-issued ones (issuer_sig was produced by the facilitator, not the
    owner).
    """
    if not kindred.is_public:
        raise ValidationError("kindred is not public")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(
        minutes=PUBLIC_INSTALL_INVITE_TTL_MINUTES
    )
    inv_body = canonical_json(
        {
            "kindred_id": str(kindred.id),
            "token": token,
            "expires_at": expires_at.isoformat(),
            "public_install": True,
        }
    )
    facilitator_sk = get_settings().facilitator_signing_key
    issuer_sig = sign(facilitator_sk, inv_body)

    inv = Invite(
        kindred_id=kindred.id,
        issued_by=kindred.created_by,
        token=token,
        expires_at=expires_at,
        max_uses=1,
        uses=0,
        issuer_sig=issuer_sig,
    )
    session.add(inv)
    await session.flush()
    await append_event(
        session,
        kindred_id=kindred.id,
        event_type="public_install_invite_minted",
        payload={"token_prefix": token[:8]},
    )
    return inv


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
