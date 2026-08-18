from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.retrieval.rrf import HybridSearchResult

RERANKER_MODEL = "ms-marco-TinyBERT-L-2-v2"


@dataclass(frozen=True, slots=True)
class RerankedSearchResult:
    score: float
    rrf_score: float
    semantic_score: float | None
    lexical_score: float | None
    raw_document_id: str
    repository_id: str
    source_type: str
    source_id: str
    source_number: int | None
    title: str
    text: str
    html_url: str
    chunk_index: int


def rerank_candidates(
    query: str,
    candidates: list[HybridSearchResult],
    *,
    limit: int = 10,
) -> list[RerankedSearchResult]:
    """Use a local cross-encoder to score query and candidate text together."""

    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("Query cannot be empty.")
    if limit < 1:
        raise ValueError("Limit must be at least 1.")
    if not candidates:
        return []

    from flashrank import RerankRequest

    passages = [
        {"id": index, "text": candidate.text}
        for index, candidate in enumerate(candidates)
    ]
    ranked_passages = _get_ranker().rerank(
        RerankRequest(query=cleaned_query, passages=passages)
    )

    return [
        _to_reranked_result(
            candidates[int(passage["id"])],
            reranker_score=float(passage["score"]),
        )
        for passage in ranked_passages[:limit]
    ]


@lru_cache(maxsize=1)
def _get_ranker() -> Any:
    from flashrank import Ranker

    return Ranker(model_name=RERANKER_MODEL)


def _to_reranked_result(
    candidate: HybridSearchResult,
    *,
    reranker_score: float,
) -> RerankedSearchResult:
    return RerankedSearchResult(
        score=reranker_score,
        rrf_score=candidate.score,
        semantic_score=candidate.semantic_score,
        lexical_score=candidate.lexical_score,
        raw_document_id=candidate.raw_document_id,
        repository_id=candidate.repository_id,
        source_type=candidate.source_type,
        source_id=candidate.source_id,
        source_number=candidate.source_number,
        title=candidate.title,
        text=candidate.text,
        html_url=candidate.html_url,
        chunk_index=candidate.chunk_index,
    )
