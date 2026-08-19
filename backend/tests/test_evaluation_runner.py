import uuid
from types import SimpleNamespace

import pytest

from app.evaluation.dataset import EvaluationDataset
from app.evaluation.runner import run_evaluation


@pytest.mark.asyncio
async def test_run_evaluation_compares_strategies_and_keeps_case_details() -> None:
    repository_id = uuid.uuid4()
    dataset = EvaluationDataset.model_validate(
        {
            "repository": "acme/billing",
            "cases": [
                {
                    "case_id": "duplicate-message",
                    "query": "Messages are processed twice.",
                    "relevant_evidence": [
                        {"source_type": "pull_request", "source_id": "184"}
                    ],
                },
                {
                    "case_id": "database-timeout",
                    "query": "Connections time out.",
                    "relevant_evidence": [
                        {"source_type": "commit", "source_id": "abc123"}
                    ],
                },
            ],
        }
    )

    async def dense(_: uuid.UUID, query: str, limit: int) -> list[SimpleNamespace]:
        assert limit == 5
        if "Messages" in query:
            return [_result("pull_request", source_id="987654", source_number=184)]
        return [_result("commit", source_id="unrelated")]

    async def bm25(_: uuid.UUID, query: str, limit: int) -> list[SimpleNamespace]:
        assert query
        assert limit == 5
        return [_result("commit", source_id="abc123")]

    report = await run_evaluation(
        repository_id,
        dataset,
        k=5,
        retrievers={"dense": dense, "bm25": bm25},
    )

    assert report.repository_id == repository_id
    assert report.strategies["dense"].aggregate.linked_fix_hit_rate == 0.5
    assert report.strategies["bm25"].aggregate.linked_fix_hit_rate == 0.5
    assert report.strategies["dense"].cases[0].ranked_ids == ["pull_request:184"]
    assert report.strategies["bm25"].cases[0].metrics.linked_fix_hit is False
    assert report.strategies["bm25"].cases[1].metrics.linked_fix_hit is True


@pytest.mark.asyncio
async def test_run_evaluation_rejects_invalid_configuration() -> None:
    dataset = EvaluationDataset.model_validate(
        {
            "repository": "acme/repo",
            "cases": [
                {
                    "case_id": "case",
                    "query": "timeout",
                    "relevant_evidence": [
                        {"source_type": "commit", "source_id": "abc123"}
                    ],
                }
            ],
        }
    )

    with pytest.raises(ValueError, match="k"):
        await run_evaluation(uuid.uuid4(), dataset, k=0)
    with pytest.raises(ValueError, match="strategy"):
        await run_evaluation(uuid.uuid4(), dataset, retrievers={})


def _result(
    source_type: str,
    *,
    source_id: str,
    source_number: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        source_type=source_type,
        source_id=source_id,
        source_number=source_number,
    )
