import math

import pytest

from app.evaluation.metrics import aggregate_evaluations, evaluate_ranking


def test_evaluate_ranking_calculates_recall_mrr_ndcg_and_hit() -> None:
    evaluation = evaluate_ranking(
        ["unrelated", "fix-a", "other", "fix-b"],
        {"fix-a", "fix-b"},
        k=3,
    )

    assert evaluation.recall_at_k == 0.5
    assert evaluation.reciprocal_rank == 0.5
    expected_ndcg = (1 / math.log2(3)) / (1 + 1 / math.log2(3))
    assert evaluation.ndcg_at_k == pytest.approx(expected_ndcg)
    assert evaluation.linked_fix_hit is True


def test_evaluate_ranking_deduplicates_repeated_chunks() -> None:
    evaluation = evaluate_ranking(
        ["same-fix", "same-fix", "unrelated"],
        {"same-fix"},
        k=2,
    )

    assert evaluation.recall_at_k == 1.0
    assert evaluation.reciprocal_rank == 1.0
    assert evaluation.ndcg_at_k == 1.0


def test_evaluate_ranking_reports_miss() -> None:
    evaluation = evaluate_ranking(["other"], {"fix"}, k=5)

    assert evaluation.recall_at_k == 0.0
    assert evaluation.reciprocal_rank == 0.0
    assert evaluation.ndcg_at_k == 0.0
    assert evaluation.linked_fix_hit is False


def test_aggregate_evaluations_averages_query_metrics() -> None:
    evaluations = [
        evaluate_ranking(["fix"], {"fix"}, k=1),
        evaluate_ranking(["other"], {"fix"}, k=1),
    ]

    aggregate = aggregate_evaluations(evaluations)

    assert aggregate.query_count == 2
    assert aggregate.recall_at_k == 0.5
    assert aggregate.mean_reciprocal_rank == 0.5
    assert aggregate.ndcg_at_k == 0.5
    assert aggregate.linked_fix_hit_rate == 0.5


def test_evaluation_rejects_missing_ground_truth_and_empty_runs() -> None:
    with pytest.raises(ValueError, match="relevant"):
        evaluate_ranking(["result"], set(), k=10)
    with pytest.raises(ValueError, match="query evaluation"):
        aggregate_evaluations([])
