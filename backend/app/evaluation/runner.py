from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from app.evaluation.dataset import EvaluationDataset
from app.evaluation.metrics import (
    AggregateEvaluation,
    QueryEvaluation,
    aggregate_evaluations,
    evaluate_ranking,
)
from app.retrieval.hybrid_search import search_hybrid
from app.retrieval.lexical_search import search_lexically
from app.retrieval.reranked_search import search_reranked
from app.retrieval.vector_store import search_similar


class SearchResult(Protocol):
    source_type: str
    source_id: str
    source_number: int | None


Retriever = Callable[[uuid.UUID, str, int], Awaitable[list[SearchResult]]]


@dataclass(frozen=True, slots=True)
class CaseEvaluationResult:
    case_id: str
    ranked_ids: list[str]
    metrics: QueryEvaluation


@dataclass(frozen=True, slots=True)
class StrategyEvaluationResult:
    strategy: str
    aggregate: AggregateEvaluation
    cases: list[CaseEvaluationResult]


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    repository_id: uuid.UUID
    dataset_repository: str
    k: int
    strategies: dict[str, StrategyEvaluationResult]


async def run_evaluation(
    repository_id: uuid.UUID,
    dataset: EvaluationDataset,
    *,
    k: int = 10,
    retrievers: dict[str, Retriever] | None = None,
) -> EvaluationReport:
    """Run every retrieval strategy against every curated evaluation case."""

    if k < 1:
        raise ValueError("k must be at least 1.")

    resolved_retrievers = _default_retrievers() if retrievers is None else retrievers
    if not resolved_retrievers:
        raise ValueError("At least one retrieval strategy is required.")

    strategies: dict[str, StrategyEvaluationResult] = {}
    for strategy, retriever in resolved_retrievers.items():
        case_results: list[CaseEvaluationResult] = []
        for case in dataset.cases:
            results = await retriever(repository_id, case.query, k)
            ranked_ids = [_canonical_result_id(result) for result in results]
            case_results.append(
                CaseEvaluationResult(
                    case_id=case.case_id,
                    ranked_ids=ranked_ids,
                    metrics=evaluate_ranking(ranked_ids, case.relevant_ids, k=k),
                )
            )

        strategies[strategy] = StrategyEvaluationResult(
            strategy=strategy,
            aggregate=aggregate_evaluations([result.metrics for result in case_results]),
            cases=case_results,
        )

    return EvaluationReport(
        repository_id=repository_id,
        dataset_repository=dataset.repository,
        k=k,
        strategies=strategies,
    )


def _canonical_result_id(result: SearchResult) -> str:
    public_id = (
        result.source_number if result.source_number is not None else result.source_id
    )
    return f"{result.source_type}:{public_id}"


def _default_retrievers() -> dict[str, Retriever]:
    return {
        "dense": search_similar,
        "bm25": search_lexically,
        "hybrid_rrf": search_hybrid,
        "hybrid_reranked": search_reranked,
    }
