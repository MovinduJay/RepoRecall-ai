from __future__ import annotations

import asyncio
import uuid

from app.retrieval.lexical_search import search_lexically
from app.retrieval.rrf import HybridSearchResult, reciprocal_rank_fusion
from app.retrieval.vector_store import search_similar

MAX_CANDIDATE_LIMIT = 50
MIN_CANDIDATE_LIMIT = 20
DEFAULT_CANDIDATE_MULTIPLIER = 3


async def search_hybrid(
    repository_id: uuid.UUID,
    query: str,
    limit: int = 10,
) -> list[HybridSearchResult]:
    """Retrieve dense and lexical candidates concurrently, then fuse with RRF."""

    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    candidate_limit = min(
        MAX_CANDIDATE_LIMIT,
        max(MIN_CANDIDATE_LIMIT, limit * DEFAULT_CANDIDATE_MULTIPLIER),
    )
    semantic_results, lexical_results = await asyncio.gather(
        search_similar(
            repository_id=repository_id,
            query=query,
            limit=candidate_limit,
        ),
        search_lexically(
            repository_id=repository_id,
            query=query,
            limit=candidate_limit,
        ),
    )

    return reciprocal_rank_fusion(
        semantic_results,
        lexical_results,
        limit=limit,
    )
