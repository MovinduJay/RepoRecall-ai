from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True, slots=True)
class QueryEvaluation:
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float
    linked_fix_hit: bool


@dataclass(frozen=True, slots=True)
class AggregateEvaluation:
    query_count: int
    recall_at_k: float
    mean_reciprocal_rank: float
    ndcg_at_k: float
    linked_fix_hit_rate: float


def evaluate_ranking(
    ranked_ids: list[str],
    relevant_ids: set[str],
    *,
    k: int,
) -> QueryEvaluation:
    """Evaluate one ranked result list using binary relevance judgments."""

    _validate_inputs(relevant_ids, k)
    unique_ranked_ids = list(dict.fromkeys(ranked_ids))
    top_k = unique_ranked_ids[:k]
    relevant_hits = [result_id in relevant_ids for result_id in top_k]
    first_relevant_rank = next(
        (
            rank
            for rank, result_id in enumerate(unique_ranked_ids, start=1)
            if result_id in relevant_ids
        ),
        None,
    )

    return QueryEvaluation(
        recall_at_k=sum(relevant_hits) / len(relevant_ids),
        reciprocal_rank=0.0 if first_relevant_rank is None else 1 / first_relevant_rank,
        ndcg_at_k=_ndcg(relevant_hits, relevant_count=len(relevant_ids), k=k),
        linked_fix_hit=any(relevant_hits),
    )


def aggregate_evaluations(
    evaluations: list[QueryEvaluation],
) -> AggregateEvaluation:
    if not evaluations:
        raise ValueError("At least one query evaluation is required.")

    return AggregateEvaluation(
        query_count=len(evaluations),
        recall_at_k=fmean(item.recall_at_k for item in evaluations),
        mean_reciprocal_rank=fmean(item.reciprocal_rank for item in evaluations),
        ndcg_at_k=fmean(item.ndcg_at_k for item in evaluations),
        linked_fix_hit_rate=fmean(float(item.linked_fix_hit) for item in evaluations),
    )


def _ndcg(relevant_hits: list[bool], *, relevant_count: int, k: int) -> float:
    discounted_cumulative_gain = sum(
        1 / math.log2(rank + 1)
        for rank, is_relevant in enumerate(relevant_hits, start=1)
        if is_relevant
    )
    ideal_hit_count = min(relevant_count, k)
    ideal_discounted_cumulative_gain = sum(
        1 / math.log2(rank + 1) for rank in range(1, ideal_hit_count + 1)
    )
    return discounted_cumulative_gain / ideal_discounted_cumulative_gain


def _validate_inputs(relevant_ids: set[str], k: int) -> None:
    if k < 1:
        raise ValueError("k must be at least 1.")
    if not relevant_ids:
        raise ValueError("At least one relevant result ID is required.")
