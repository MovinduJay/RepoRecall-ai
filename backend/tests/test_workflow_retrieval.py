import uuid
from unittest.mock import AsyncMock

import pytest

from app.retrieval.reranker import RerankedSearchResult
from app.workflow import retrieval
from app.workflow.state import create_initial_state


@pytest.mark.asyncio
async def test_retrieve_candidates_uses_original_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_id = uuid.uuid4()
    state = create_initial_state("database timeout", str(repository_id))
    expected = [_result()]
    search_reranked = AsyncMock(return_value=expected)
    monkeypatch.setattr(retrieval, "search_reranked", search_reranked)

    updates = await retrieval.retrieve_candidates(state)

    assert updates == {"retrieved_results": expected}
    search_reranked.assert_awaited_once_with(
        repository_id=repository_id,
        query="database timeout",
        limit=retrieval.DEFAULT_RETRIEVAL_LIMIT,
    )


@pytest.mark.asyncio
async def test_retrieve_candidates_uses_latest_rewritten_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_id = uuid.uuid4()
    state = create_initial_state("database timeout", str(repository_id))
    state["rewritten_queries"] = ["connection failure", "pool exhausted TimeoutError"]
    search_reranked = AsyncMock(return_value=[])
    monkeypatch.setattr(retrieval, "search_reranked", search_reranked)

    await retrieval.retrieve_candidates(state)

    assert search_reranked.await_args.kwargs["query"] == "pool exhausted TimeoutError"


@pytest.mark.asyncio
async def test_retrieve_candidates_rejects_invalid_repository_id() -> None:
    state = create_initial_state("database timeout", "not-a-uuid")

    with pytest.raises(ValueError, match="valid UUID"):
        await retrieval.retrieve_candidates(state)


def _result() -> RerankedSearchResult:
    return RerankedSearchResult(
        score=0.9,
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
