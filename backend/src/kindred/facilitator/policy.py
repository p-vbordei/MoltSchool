"""Policy engine — deterministic membership/scope/expiry/tier checks.

Absorbs Plan 01 follow-ups I1 (membership), I2 (expiry), I4 (scope). All checks
are equality/set-membership — no LLM anywhere. /ask composes them via
`require_agent_authorized` before any retrieval happens.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.errors import UnauthorizedError
from kindred.models.agent import Agent
from kindred.models.membership import AgentKindredMembership

if TYPE_CHECKING:
    from kindred.models.artifact import Artifact


async def require_member(
    session: AsyncSession, *, agent_pubkey: bytes, kindred_id: UUID
) -> AgentKindredMembership:
    """Raise UnauthorizedError if the agent is not a member of the kindred."""
    q = (
        select(AgentKindredMembership)
        .join(Agent, Agent.id == AgentKindredMembership.agent_id)
        .where(Agent.pubkey == agent_pubkey)
        .where(AgentKindredMembership.kindred_id == kindred_id)
    )
    m = (await session.execute(q)).scalar_one_or_none()
    if m is None:
        raise UnauthorizedError("agent is not a member of this kindred")
    return m


def require_scope(
    scope: dict | str, *, action: str, kindred_slug: str
) -> None:
    """Check the agent's attestation scope permits (action, kindred_slug).

    Accepts a dict or JSON-encoded string. Wildcard `"*"` in kindreds is honored.
    """
    parsed: dict[str, Any]
    parsed = json.loads(scope) if isinstance(scope, str) else scope
    actions = parsed.get("actions", []) or []
    kindreds = parsed.get("kindreds", []) or []
    if action not in actions:
        raise UnauthorizedError(f"action {action!r} not in agent scope")
    if "*" not in kindreds and kindred_slug not in kindreds:
        raise UnauthorizedError(f"kindred {kindred_slug!r} not in agent scope")


def require_not_expired(expires_at: datetime) -> None:
    """Raise UnauthorizedError if the attestation has expired."""
    # sqlite+aiosqlite returns naive datetimes for DateTime(timezone=True);
    # treat them as UTC for the comparison.
    normalized = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=UTC)
    if normalized < datetime.now(UTC):
        raise UnauthorizedError("agent attestation has expired")


async def require_agent_authorized(
    session: AsyncSession, *, agent_pubkey: bytes, kindred_id: UUID,
    kindred_slug: str, action: str,
) -> Agent:
    """Compose membership + scope + expiry in one call. Returns the agent row."""
    await require_member(session, agent_pubkey=agent_pubkey, kindred_id=kindred_id)
    agent = (
        await session.execute(select(Agent).where(Agent.pubkey == agent_pubkey))
    ).scalar_one_or_none()
    if agent is None:
        # Shouldn't happen after require_member — defensive.
        raise UnauthorizedError("agent not found")
    require_scope(agent.attestation_scope, action=action, kindred_slug=kindred_slug)
    require_not_expired(agent.attestation_expires_at)
    return agent


def filter_by_tier(
    artifacts_with_tiers: list[tuple[Artifact, str]],
    *,
    include_peer_shared: bool = False,
) -> list[tuple[Artifact, str]]:
    """Drop peer-shared artefacts unless the caller explicitly opts in."""
    if include_peer_shared:
        return list(artifacts_with_tiers)
    return [(a, t) for a, t in artifacts_with_tiers if t == "class-blessed"]
