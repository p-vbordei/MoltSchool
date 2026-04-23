"""Librarian — RAG retrieval over artefact embeddings.

Computes cosine similarity in Python between the query embedding and each
artefact's stored embedding. Filters out:
  - artefacts without embeddings (backward-compat column is nullable)
  - artefacts whose validity window has lapsed (unless `include_expired=True`)

At <1000 artefacte per kindred, in-Python cosine is fine. TODO: once a single
kindred's corpus outgrows this, switch to pgvector HNSW — ordering would then be
`q.order_by(Artifact.embedding.cosine_distance(qv)).limit(k)` plus an index
migration. See plan 02 §Task 5 and plan 07 follow-ups.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.embeddings.provider import EmbeddingProvider
from kindred.models.artifact import Artifact


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity. Returns 0.0 if either vector is zero/length mismatched."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


async def retrieve_top_k(
    session: AsyncSession,
    *,
    kindred_id: UUID,
    query: str,
    provider: EmbeddingProvider,
    k: int = 5,
    include_expired: bool = False,
) -> tuple[list[tuple[Artifact, float]], int]:
    """Return ((artifact, similarity) top-K, expired_shadow_count).

    expired_shadow_count: count of artefacts that WOULD have been in the top-K
    if the expiry filter were disabled. Zero when include_expired=True. Powers
    the staleness-cost telemetry — the "opportunity cost" of filtering expired
    knowledge.

    Applies validity-window filter (I6) so expired artefacts never bubble up to
    the caller unless explicitly requested (e.g. rollback tooling).
    """
    query_vec = await provider.embed(query)
    now = datetime.now(UTC)

    # Load all artefacts regardless of expiry — we're already scanning the full
    # corpus in Python (cosine), so filtering is free.
    stmt = select(Artifact).where(Artifact.kindred_id == kindred_id)
    artifacts = list((await session.execute(stmt)).scalars())

    scored_all: list[tuple[Artifact, float]] = []
    for art in artifacts:
        if art.embedding is None:
            continue
        scored_all.append((art, _cosine(query_vec, art.embedding)))
    scored_all.sort(key=lambda p: p[1], reverse=True)

    if include_expired:
        return scored_all[:k], 0

    def _expired(a: Artifact) -> bool:
        # SQLite in tests drops tzinfo even for timezone=True columns — treat
        # naive datetimes as UTC so comparison with tz-aware `now` works.
        vu = a.valid_until
        if vu.tzinfo is None:
            vu = vu.replace(tzinfo=UTC)
        return vu <= now

    top_k_with_expired = scored_all[:k]
    expired_shadow = sum(1 for a, _ in top_k_with_expired if _expired(a))
    scored_fresh = [(a, s) for a, s in scored_all if not _expired(a)][:k]
    return scored_fresh, expired_shadow
