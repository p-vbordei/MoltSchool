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
) -> list[tuple[Artifact, float]]:
    """Return up to `k` (artifact, similarity) pairs sorted by desc similarity.

    Applies validity-window filter (I6) so expired artefacts never bubble up to
    the caller unless explicitly requested (e.g. rollback tooling).
    """
    query_vec = await provider.embed(query)

    stmt = select(Artifact).where(Artifact.kindred_id == kindred_id)
    if not include_expired:
        stmt = stmt.where(Artifact.valid_until > datetime.now(UTC))
    artifacts = list((await session.execute(stmt)).scalars())

    scored: list[tuple[Artifact, float]] = []
    for art in artifacts:
        if art.embedding is None:
            continue
        scored.append((art, _cosine(query_vec, art.embedding)))
    scored.sort(key=lambda p: p[1], reverse=True)
    return scored[:k]
