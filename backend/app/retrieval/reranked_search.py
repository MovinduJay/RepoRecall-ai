from __future__ import annotations

import asyncio
import uuid

from app.retrieval.hybrid_search import search_hybrid
from app.retrieval.reranker import RerankedSearchResult, rerank_candidates

MAX_RERANK_CANDIDATES = 50
MIN_RERANK_CANDIDATES = 20
RERANK_CANDIDATE_MULTIPLIER = 3


async def search_reranked(
    repository_id: uuid.UUID,
    query: str,
    limit: int = 10,
) -> list[RerankedSearchResult]:
    """Retrieve hybrid candidates and rerank them with a cross-encoder."""

    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    candidate_limit = min(
        MAX_RERANK_CANDIDATES,
        max(MIN_RERANK_CANDIDATES, limit * RERANK_CANDIDATE_MULTIPLIER),
    )
    candidates = await search_hybrid(
        repository_id=repository_id,
        query=query,
        limit=candidate_limit,
    )
    return await asyncio.to_thread(
        rerank_candidates,
        query,
        candidates,
        limit=limit,
    )
