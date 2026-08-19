import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.evaluation.metrics import AggregateEvaluation, QueryEvaluation
from app.evaluation.runner import (
    CaseEvaluationResult,
    EvaluationReport,
    StrategyEvaluationResult,
)
from app.scripts import evaluate_retrieval


@pytest.mark.asyncio
async def test_run_loads_dataset_prints_summary_and_writes_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository_id = uuid.uuid4()
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            {
                "repository": "acme/repo",
                "cases": [
                    {
                        "case_id": "timeout",
                        "query": "Database timeout",
                        "relevant_evidence": [
                            {"source_type": "commit", "source_id": "abc123"}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report = _report(repository_id)
    run_evaluation = AsyncMock(return_value=report)
    monkeypatch.setattr(evaluate_retrieval, "run_evaluation", run_evaluation)
    output_path = tmp_path / "reports" / "result.json"

    result = await evaluate_retrieval.run(
        repository_id,
        dataset_path,
        k=10,
        output_path=output_path,
    )

    assert result == report
    run_evaluation.assert_awaited_once()
    assert run_evaluation.await_args.kwargs["k"] == 10
    serialized = json.loads(output_path.read_text(encoding="utf-8"))
    assert serialized["repository_id"] == str(repository_id)
    assert serialized["strategies"]["dense"]["aggregate"]["recall_at_k"] == 1.0
    output = capsys.readouterr().out
    assert "dense" in output
    assert "Report written" in output


def _report(repository_id: uuid.UUID) -> EvaluationReport:
    metrics = QueryEvaluation(
        recall_at_k=1.0,
        reciprocal_rank=1.0,
        ndcg_at_k=1.0,
        linked_fix_hit=True,
    )
    aggregate = AggregateEvaluation(
        query_count=1,
        recall_at_k=1.0,
        mean_reciprocal_rank=1.0,
        ndcg_at_k=1.0,
        linked_fix_hit_rate=1.0,
    )
    return EvaluationReport(
        repository_id=repository_id,
        dataset_repository="acme/repo",
        k=10,
        strategies={
            "dense": StrategyEvaluationResult(
                strategy="dense",
                aggregate=aggregate,
                cases=[
                    CaseEvaluationResult(
                        case_id="timeout",
                        ranked_ids=["commit:abc123"],
                        metrics=metrics,
                    )
                ],
            )
        },
    )
