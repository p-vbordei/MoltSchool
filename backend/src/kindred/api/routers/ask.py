"""POST /v1/kindreds/{slug}/ask — RAG retrieve + policy + framing + audit.

Flow (absorbs Plan 01 follow-ups I1/I2/I4/I6/I7):
  1. Parse agent pubkey from header
  2. Resolve kindred by slug
  3. require_agent_authorized → membership + scope + expiry
  4. sanitize_query → 400 on oversize
  5. detect_injection_patterns → 400 and audit-log the attempt
  6. retrieve_top_k (validity filter applied inside)
  7. compute_tier per artefact; filter_by_tier drops peer-shared by default
  8. frame_artifact + ProvenanceChip per result
  9. append_audit with facilitator signature

No LLM generation anywhere — the Facilitator only retrieves and frames.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import (
    db_session,
    get_embedding_provider,
    get_settings,
)
from kindred.api.schemas.ask import AskReq, AskResp, ProvenanceChip
from kindred.config import Settings
from kindred.crypto.keys import pubkey_to_str, str_to_pubkey
from kindred.embeddings.provider import EmbeddingProvider
from kindred.facilitator.librarian import retrieve_top_k
from kindred.facilitator.policy import filter_by_tier, require_agent_authorized
from kindred.facilitator.sanitizer import (
    detect_injection_patterns,
    frame_artifact,
    sanitize_query,
)
from kindred.services.audit import append_audit
from kindred.services.blessings import compute_tier
from kindred.services.kindreds import get_kindred_by_slug

router = APIRouter()


def _success_rate(uses: int, successes: int) -> float:
    return (successes / uses) if uses > 0 else 0.0


async def _parse_agent_pubkey(x_agent_pubkey: str = Header(...)) -> bytes:
    try:
        return str_to_pubkey(x_agent_pubkey)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.post("/{slug}/ask", response_model=AskResp)
async def ask(
    slug: str,
    req: AskReq,
    session: AsyncSession = Depends(db_session),
    provider: EmbeddingProvider = Depends(get_embedding_provider),
    settings: Settings = Depends(get_settings),
    agent_pubkey: bytes = Depends(_parse_agent_pubkey),
):
    k = await get_kindred_by_slug(session, slug)
    # Policy: membership + scope + expiry (I1 + I2 + I4)
    await require_agent_authorized(
        session, agent_pubkey=agent_pubkey, kindred_id=k.id,
        kindred_slug=slug, action="read",
    )

    # Sanitize — 400 on oversize
    try:
        q = sanitize_query(req.query)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    hits = detect_injection_patterns(q)
    if hits:
        # Audit the blocked attempt, then 400.
        blocked_payload = {
            "query": q,
            "artifact_ids_returned": [],
            "scores": [],
            "tiers": [],
            "k": req.k,
            "expired_shadow_hits": 0,
            "blocked_injection": True,
            "patterns": [h.pattern for h in hits],
        }
        await append_audit(
            session, kindred_id=k.id, agent_pubkey=agent_pubkey,
            action="ask", payload=blocked_payload,
            facilitator_sk=settings.facilitator_signing_key,
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": "injection_detected",
                "patterns": [h.pattern for h in hits],
            },
        )

    # Retrieve (validity filter inside — I6)
    scored, expired_shadow = await retrieve_top_k(
        session, kindred_id=k.id, query=q, provider=provider, k=req.k,
    )
    # Compute tier alongside score — keep a single ordered list.
    scored_with_tier: list[tuple] = []
    for art, score in scored:
        tier = await compute_tier(session, artifact=art, threshold=k.bless_threshold)
        scored_with_tier.append((art, score, tier))

    # filter_by_tier takes (artifact, tier) pairs — adapt.
    tier_filtered = filter_by_tier(
        [(a, t) for a, _s, t in scored_with_tier],
        include_peer_shared=req.include_peer_shared,
    )
    # Re-align score + tier with the filtered content_ids.
    score_by_cid = {a.content_id: s for a, s, _t in scored_with_tier}
    tier_by_cid = {a.content_id: t for a, _s, t in scored_with_tier}
    filtered = tier_filtered  # downstream framing code uses `filtered`

    # Frame + provenance
    artifacts_out = []
    chips: list[ProvenanceChip] = []
    for art, tier in filtered:
        framed = frame_artifact(
            content_id=art.content_id,
            tier=tier,
            author_pubkey=pubkey_to_str(art.author_pubkey),
            content=f"{art.logical_name} ({', '.join(art.tags or [])})",
        )
        artifacts_out.append({
            "content_id": art.content_id,
            "tier": tier,
            "framed": framed,
        })
        chips.append(ProvenanceChip(
            content_id=art.content_id,
            logical_name=art.logical_name,
            type=art.type,
            tier=tier,
            author_pubkey=pubkey_to_str(art.author_pubkey),
            outcome_success_rate=_success_rate(art.outcome_uses, art.outcome_successes),
            valid_until=art.valid_until.isoformat(),
        ))

    # Live audit log of the successful ask (I7).
    audit = await append_audit(
        session, kindred_id=k.id, agent_pubkey=agent_pubkey,
        action="ask",
        payload={
            "query": q,
            "artifact_ids_returned": [a.content_id for a, _ in filtered],
            "scores": [score_by_cid[a.content_id] for a, _ in filtered],
            "tiers": [tier_by_cid[a.content_id] for a, _ in filtered],
            "k": req.k,
            "expired_shadow_hits": expired_shadow,
            "blocked_injection": False,
        },
        facilitator_sk=settings.facilitator_signing_key,
    )

    return AskResp(
        audit_id=str(audit.id),
        artifacts=artifacts_out,
        provenance=chips,
        blocked_injection=False,
    )
