from __future__ import annotations

from typing import Any, Literal, NotRequired, Required, TypedDict

from app.retrieval.reranker import RerankedSearchResult


class InvestigationState(TypedDict, total=False):
    query: Required[str]
    repository_id: Required[str]
    extracted_errors: list[str]
    extracted_paths: list[str]
    metadata_filters: dict[str, Any]
    rewritten_queries: list[str]
    retrieved_results: list[RerankedSearchResult]
    confidence: float
    retry_count: int
    decision: NotRequired[Literal["sufficient", "rewrite", "abstain"]]
    answer: NotRequired[str | None]
    citations: list[str]
    generation_error: NotRequired[str | None]


def create_initial_state(query: str, repository_id: str) -> InvestigationState:
    cleaned_query = query.strip()
    cleaned_repository_id = repository_id.strip()
    if not cleaned_query:
        raise ValueError("Query cannot be empty.")
    if not cleaned_repository_id:
        raise ValueError("Repository ID cannot be empty.")

    return InvestigationState(
        query=cleaned_query,
        repository_id=cleaned_repository_id,
        extracted_errors=[],
        extracted_paths=[],
        metadata_filters={},
        rewritten_queries=[],
        retrieved_results=[],
        confidence=0.0,
        retry_count=0,
        answer=None,
        citations=[],
        generation_error=None,
    )
