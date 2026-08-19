import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from app.retrieval import reranked_search
from app.retrieval.reranker import RerankedSearchResult
from app.retrieval.rrf import HybridSearchResult


@pytest.mark.asyncio
async def test_search_reranked_loads_wider_candidate_set_and_runs_reranker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_id = uuid.uuid4()
    candidates = [_candidate("one")]
    expected = [_reranked_result("one")]
    hybrid_search = AsyncMock(return_value=candidates)
    rerank = Mock(return_value=expected)
    monkeypatch.setattr(reranked_search, "search_hybrid", hybrid_search)
    monkeypatch.setattr(reranked_search, "rerank_candidates", rerank)

    results = await reranked_search.search_reranked(
        repository_id,
        "database timeout",
        limit=5,
    )

    hybrid_search.assert_awaited_once_with(
        repository_id=repository_id,
        query="database timeout",
        limit=20,
    )
    rerank.assert_called_once_with("database timeout", candidates, limit=20)
    assert results == expected


@pytest.mark.asyncio
async def test_search_reranked_caps_candidate_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hybrid_search = AsyncMock(return_value=[])
    monkeypatch.setattr(reranked_search, "search_hybrid", hybrid_search)

    await reranked_search.search_reranked(uuid.uuid4(), "timeout", limit=50)

    assert hybrid_search.await_args.kwargs["limit"] == 50


def _candidate(source_id: str) -> HybridSearchResult:
    return HybridSearchResult(
        score=0.03,
        semantic_score=0.8,
        lexical_score=4.0,
        raw_document_id=f"document-{source_id}",
        repository_id="repository-1",
        source_type="issue",
        source_id=source_id,
        source_number=1,
        title=source_id,
        text=f"Text for {source_id}",
        html_url=f"https://github.com/acme/repo/issues/{source_id}",
        chunk_index=0,
    )


def _reranked_result(source_id: str) -> RerankedSearchResult:
    candidate = _candidate(source_id)
    return RerankedSearchResult(
        score=0.9,
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
