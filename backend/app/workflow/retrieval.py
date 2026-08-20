from __future__ import annotations

import uuid

from app.retrieval.reranked_search import search_reranked
from app.retrieval.reranker import RerankedSearchResult
from app.workflow.state import InvestigationState

DEFAULT_RETRIEVAL_LIMIT = 10


async def retrieve_candidates(
    state: InvestigationState,
) -> dict[str, list[RerankedSearchResult]]:
    """Retrieve evidence for the active original or rewritten query."""

    repository_id = _parse_repository_id(state["repository_id"])
    query = _active_query(state)
    results = await search_reranked(
        repository_id=repository_id,
        query=query,
        limit=DEFAULT_RETRIEVAL_LIMIT,
    )
    return {"retrieved_results": results}


def _active_query(state: InvestigationState) -> str:
    rewritten_queries = state.get("rewritten_queries", [])
    return rewritten_queries[-1] if rewritten_queries else state["query"]


def _parse_repository_id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as error:
        raise ValueError("Repository ID must be a valid UUID.") from error
