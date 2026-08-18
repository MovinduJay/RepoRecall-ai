from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class RankedChunk(Protocol):
    score: float
    raw_document_id: str
    repository_id: str
    source_type: str
    source_id: str
    source_number: int | None
    title: str
    text: str
    html_url: str
    chunk_index: int


@dataclass(frozen=True, slots=True)
class HybridSearchResult:
    score: float
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


def reciprocal_rank_fusion(
    semantic_results: list[RankedChunk],
    lexical_results: list[RankedChunk],
    *,
    limit: int = 10,
    rank_constant: int = 60,
) -> list[HybridSearchResult]:
    """Fuse two rankings with RRF: sum 1 / (rank_constant + rank)."""

    if limit < 1:
        raise ValueError("Limit must be at least 1.")
    if rank_constant < 1:
        raise ValueError("Rank constant must be at least 1.")

    candidates: dict[tuple[str, int], RankedChunk] = {}
    fused_scores: dict[tuple[str, int], float] = {}
    semantic_scores: dict[tuple[str, int], float] = {}
    lexical_scores: dict[tuple[str, int], float] = {}

    _add_ranking(
        semantic_results,
        candidates=candidates,
        fused_scores=fused_scores,
        source_scores=semantic_scores,
        rank_constant=rank_constant,
    )
    _add_ranking(
        lexical_results,
        candidates=candidates,
        fused_scores=fused_scores,
        source_scores=lexical_scores,
        rank_constant=rank_constant,
    )

    ordered_keys = sorted(
        candidates,
        key=lambda key: (-fused_scores[key], key[0], key[1]),
    )[:limit]

    return [
        _to_hybrid_result(
            candidates[key],
            fused_score=fused_scores[key],
            semantic_score=semantic_scores.get(key),
            lexical_score=lexical_scores.get(key),
        )
        for key in ordered_keys
    ]


def _add_ranking(
    results: list[RankedChunk],
    *,
    candidates: dict[tuple[str, int], RankedChunk],
    fused_scores: dict[tuple[str, int], float],
    source_scores: dict[tuple[str, int], float],
    rank_constant: int,
) -> None:
    for rank, result in enumerate(results, start=1):
        key = (result.raw_document_id, result.chunk_index)
        candidates.setdefault(key, result)
        fused_scores[key] = fused_scores.get(key, 0.0) + 1 / (rank_constant + rank)
        source_scores[key] = result.score


def _to_hybrid_result(
    result: RankedChunk,
    *,
    fused_score: float,
    semantic_score: float | None,
    lexical_score: float | None,
) -> HybridSearchResult:
    return HybridSearchResult(
        score=fused_score,
        semantic_score=semantic_score,
        lexical_score=lexical_score,
        raw_document_id=result.raw_document_id,
        repository_id=result.repository_id,
        source_type=result.source_type,
        source_id=result.source_id,
        source_number=result.source_number,
        title=result.title,
        text=result.text,
        html_url=result.html_url,
        chunk_index=result.chunk_index,
    )
