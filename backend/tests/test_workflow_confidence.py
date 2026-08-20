import pytest

from app.retrieval.reranker import RerankedSearchResult
from app.workflow.confidence import assess_confidence, route_after_confidence
from app.workflow.state import create_initial_state


def test_assess_confidence_accepts_strong_evidence() -> None:
    state = create_initial_state("database timeout", "repository-id")
    state["retrieved_results"] = [_result(score=0.8)]

    updates = assess_confidence(state, threshold=0.5)

    assert updates == {"confidence": 0.8, "decision": "sufficient"}


def test_assess_confidence_requests_only_one_retry() -> None:
    state = create_initial_state("database timeout", "repository-id")
    state["retrieved_results"] = [_result(score=0.1)]

    first_updates = assess_confidence(state, threshold=0.5)
    state.update(first_updates)  # type: ignore[typeddict-item]
    assert route_after_confidence(state) == "rewrite"

    state["retry_count"] = 1
    exhausted_updates = assess_confidence(state, threshold=0.5)

    assert exhausted_updates == {"confidence": 0.1, "decision": "abstain"}


def test_assess_confidence_treats_no_results_as_weak() -> None:
    state = create_initial_state("database timeout", "repository-id")

    assert assess_confidence(state, threshold=0.5) == {
        "confidence": 0.0,
        "decision": "rewrite",
    }


def test_confidence_validation_and_routing_require_valid_state() -> None:
    state = create_initial_state("database timeout", "repository-id")

    with pytest.raises(ValueError, match="between"):
        assess_confidence(state, threshold=1.1)
    with pytest.raises(ValueError, match="missing"):
        route_after_confidence(state)


def _result(*, score: float) -> RerankedSearchResult:
    return RerankedSearchResult(
        score=score,
        rrf_score=0.03,
        semantic_score=0.8,
        lexical_score=4.0,
        raw_document_id="document-1",
        repository_id="repository-1",
        source_type="pull_request",
        source_id="123",
        source_number=10,
        title="Fix timeout",
        text="Increase connection pool timeout.",
        html_url="https://github.com/acme/repo/pull/10",
        chunk_index=0,
    )
