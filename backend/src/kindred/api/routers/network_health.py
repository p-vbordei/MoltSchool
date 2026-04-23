"""GET /v1/kindreds/{slug}/health — network-health indicators."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session
from kindred.api.schemas.health import KindredHealthResp
from kindred.crypto.keys import str_to_pubkey
from kindred.facilitator.policy import require_agent_authorized
from kindred.services.health import (
    compute_retrieval_utility,
    compute_staleness_cost,
    compute_trust_propagation,
    compute_ttfur,
)
from kindred.services.kindreds import get_kindred_by_slug

router = APIRouter()


async def _parse_agent_pubkey(x_agent_pubkey: str = Header(...)) -> bytes:
    try:
        return str_to_pubkey(x_agent_pubkey)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.get("/{slug}/health", response_model=KindredHealthResp)
async def health(
    slug: str,
    session: AsyncSession = Depends(db_session),
    agent_pubkey: bytes = Depends(_parse_agent_pubkey),
) -> KindredHealthResp:
    k = await get_kindred_by_slug(session, slug)
    await require_agent_authorized(
        session, agent_pubkey=agent_pubkey, kindred_id=k.id,
        kindred_slug=slug, action="read",
    )
    ru = await compute_retrieval_utility(session, kindred_id=k.id)
    tt = await compute_ttfur(session, kindred_id=k.id)
    tp = await compute_trust_propagation(session, kindred_id=k.id, threshold=k.bless_threshold)
    sc = await compute_staleness_cost(session, kindred_id=k.id)
    return KindredHealthResp(
        kindred_slug=slug,
        generated_at=datetime.now(UTC).isoformat(),
        retrieval_utility=ru,
        ttfur=tt,
        trust_propagation=tp,
        staleness_cost=sc,
    )
