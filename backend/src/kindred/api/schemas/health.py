from __future__ import annotations

from pydantic import BaseModel


class RetrievalUtility(BaseModel):
    total_asks: int
    total_outcomes: int
    success_rate: float          # successes / outcomes (0.0 when no outcomes)
    mean_rank_of_chosen: float   # avg zero-indexed rank (0.0 when no outcomes)
    top1_precision: float        # fraction of outcomes where rank_of_chosen == 0


class TTFUR(BaseModel):
    sample_size: int
    p50_seconds: float | None
    p90_seconds: float | None


class TrustPropagation(BaseModel):
    promoted_artifacts: int      # artefacte that hit bless_threshold
    p50_seconds: float | None    # median publish → tier-blessed
    p90_seconds: float | None


class StalenessCost(BaseModel):
    shadow_hits_last_7d: int     # asks where expired artefact would have made top-K
    expiring_soon_hits_last_7d: int  # asks where returned artifact expires within 7d


class KindredHealthResp(BaseModel):
    kindred_slug: str
    generated_at: str            # ISO 8601 UTC
    retrieval_utility: RetrievalUtility
    ttfur: TTFUR
    trust_propagation: TrustPropagation
    staleness_cost: StalenessCost
