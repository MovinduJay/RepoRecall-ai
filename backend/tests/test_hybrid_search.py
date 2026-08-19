import uuid
from unittest.mock import AsyncMock

import pytest

from app.retrieval import hybrid_search
from app.retrieval.lexical_search import LexicalSearchResult
from app.retrieval.vector_store import SemanticSearchResult


@pytest.mark.asyncio
async def test_search_hybrid_retrieves_candidates_and_fuses_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_id = uuid.uuid4()
    semantic_result = _semantic_result("shared", 0.81)
    lexical_result = LexicalSearchResult(**vars(_semantic_result("shared", 4.2)))
    semantic_search = AsyncMock(return_value=[semantic_result])
    lexical_search = AsyncMock(return_value=[lexical_result])
    monkeypatch.setattr(hybrid_search, "search_similar", semantic_search)
    monkeypatch.setattr(hybrid_search, "search_lexically", lexical_search)

    results = await hybrid_search.search_hybrid(repository_id, "database timeout", limit=5)

    semantic_search.assert_awaited_once_with(
        repository_id=repository_id,
        query="database timeout",
        limit=20,
    )
    lexical_search.assert_awaited_once_with(
        repository_id=repository_id,
        query="database timeout",
        limit=20,
    )
    assert len(results) == 1
    assert results[0].semantic_score == 0.81
    assert results[0].lexical_score == 4.2


@pytest.mark.asyncio
async def test_search_hybrid_caps_candidate_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantic_search = AsyncMock(return_value=[])
    lexical_search = AsyncMock(return_value=[])
    monkeypatch.setattr(hybrid_search, "search_similar", semantic_search)
    monkeypatch.setattr(hybrid_search, "search_lexically", lexical_search)

    await hybrid_search.search_hybrid(uuid.uuid4(), "timeout", limit=50)

    assert semantic_search.await_args.kwargs["limit"] == 50
    assert lexical_search.await_args.kwargs["limit"] == 50


@pytest.mark.asyncio
async def test_search_hybrid_returns_distinct_source_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_chunk = _semantic_result("same", 0.9)
    second_chunk = SemanticSearchResult(
        **{**vars(first_chunk), "score": 0.8, "chunk_index": 1}
    )
    other_document = _semantic_result("other", 0.7)
    semantic_search = AsyncMock(
        return_value=[first_chunk, second_chunk, other_document]
    )
    lexical_search = AsyncMock(return_value=[])
    monkeypatch.setattr(hybrid_search, "search_similar", semantic_search)
    monkeypatch.setattr(hybrid_search, "search_lexically", lexical_search)

    results = await hybrid_search.search_hybrid(uuid.uuid4(), "timeout", limit=2)

    assert [result.raw_document_id for result in results] == [
        "document-same",
        "document-other",
    ]


def _semantic_result(source_id: str, score: float) -> SemanticSearchResult:
    return SemanticSearchResult(
        score=score,
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
