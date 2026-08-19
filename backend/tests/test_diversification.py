import pytest

from app.retrieval.diversification import diversify_by_source
from app.retrieval.vector_store import SemanticSearchResult


def test_diversify_by_source_keeps_best_ranked_chunk_per_document() -> None:
    results = [
        _result("document-one", chunk_index=1, score=0.9),
        _result("document-one", chunk_index=0, score=0.8),
        _result("document-two", chunk_index=0, score=0.7),
    ]

    diversified = diversify_by_source(results, limit=2)

    assert [(item.raw_document_id, item.chunk_index) for item in diversified] == [
        ("document-one", 1),
        ("document-two", 0),
    ]


def test_diversify_by_source_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError, match="Limit"):
        diversify_by_source([], limit=0)


def _result(
    raw_document_id: str,
    *,
    chunk_index: int,
    score: float,
) -> SemanticSearchResult:
    return SemanticSearchResult(
        score=score,
        raw_document_id=raw_document_id,
        repository_id="repository-1",
        source_type="issue",
        source_id=raw_document_id,
        source_number=1,
        title=raw_document_id,
        text=f"Chunk {chunk_index}",
        html_url="https://github.com/acme/repo/issues/1",
        chunk_index=chunk_index,
    )
