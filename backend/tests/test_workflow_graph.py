import uuid
from unittest.mock import AsyncMock

import pytest

from app.generation.provider import GeneratedAnswer
from app.retrieval.reranker import RerankedSearchResult
from app.workflow import graph
from app.workflow.state import create_initial_state


@pytest.mark.asyncio
async def test_graph_ends_with_sufficient_evidence_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retrieve = AsyncMock(return_value={"retrieved_results": [_result(score=0.8)]})
    monkeypatch.setattr(graph, "retrieve_candidates", retrieve)
    workflow = graph.build_investigation_graph()

    result = await workflow.ainvoke(
        create_initial_state("TimeoutError in app/db.py", str(uuid.uuid4()))
    )

    assert result["decision"] == "sufficient"
    assert result["retry_count"] == 0
    assert result["extracted_errors"] == ["TimeoutError"]
    assert result["extracted_paths"] == ["app/db.py"]
    assert retrieve.await_count == 1


@pytest.mark.asyncio
async def test_graph_generates_answer_only_on_sufficient_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = _result(score=0.8)
    retrieve = AsyncMock(return_value={"retrieved_results": [evidence]})
    provider = AsyncMock()
    provider.generate.return_value = GeneratedAnswer(
        answer="PR #10 increased the connection timeout.",
        citations=[evidence.html_url],
    )
    monkeypatch.setattr(graph, "retrieve_candidates", retrieve)
    workflow = graph.build_investigation_graph(answer_provider=provider)

    result = await workflow.ainvoke(
        create_initial_state("TimeoutError in app/db.py", str(uuid.uuid4()))
    )

    assert result["decision"] == "sufficient"
    assert result["answer"] == "PR #10 increased the connection timeout."
    assert result["citations"] == [evidence.html_url]
    provider.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_graph_rewrites_once_then_accepts_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retrieve = AsyncMock(
        side_effect=[
            {"retrieved_results": []},
            {"retrieved_results": [_result(score=0.8)]},
        ]
    )
    monkeypatch.setattr(graph, "retrieve_candidates", retrieve)
    workflow = graph.build_investigation_graph()

    result = await workflow.ainvoke(
        create_initial_state("TimeoutError in app/db.py", str(uuid.uuid4()))
    )

    assert result["decision"] == "sufficient"
    assert result["retry_count"] == 1
    assert len(result["rewritten_queries"]) == 1
    assert retrieve.await_count == 2


@pytest.mark.asyncio
async def test_graph_abstains_after_retry_remains_weak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retrieve = AsyncMock(return_value={"retrieved_results": []})
    provider = AsyncMock()
    monkeypatch.setattr(graph, "retrieve_candidates", retrieve)
    workflow = graph.build_investigation_graph(answer_provider=provider)

    result = await workflow.ainvoke(
        create_initial_state("Unknown failure", str(uuid.uuid4()))
    )

    assert result["decision"] == "abstain"
    assert result["retry_count"] == 1
    assert result["answer"] == graph.ABSTENTION_MESSAGE
    assert result["citations"] == []
    assert retrieve.await_count == 2
    provider.generate.assert_not_awaited()


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
