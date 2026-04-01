from __future__ import annotations

from ads_platform.ranking.base import MultiSlotAllocator
from ads_platform.schemas.ranking import AuctionResult, ScoredCandidate


class TopKAllocator(MultiSlotAllocator):
    def allocate(
        self,
        request_id: str,
        scored_candidates: list[ScoredCandidate],
        num_slots: int,
    ) -> AuctionResult:
        ranked = sorted(
            scored_candidates,
            key=lambda x: (x.rank_score, x.candidate.ad_id),
            reverse=True,
        )
        winners = ranked[:num_slots]
        dropped = ranked[num_slots:]
        return AuctionResult(
            request_id=request_id,
            winners=winners,
            dropped=dropped,
            debug={"num_candidates": len(scored_candidates), "num_slots": num_slots},
        )
