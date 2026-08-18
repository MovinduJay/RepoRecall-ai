from types import SimpleNamespace

import pytest

from app.retrieval import reranker
from app.retrieval.rrf import HybridSearchResult


def test_rerank_candidates_uses_cross_encoder_order_and_preserves_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates = [_candidate("first", 0.032), _candidate("second", 0.029)]
    ranker = SimpleNamespace(
        rerank=lambda request: [
            {"id": 1, "score": 0.91},
            {"id": 0, "score": 0.12},
        ]
    )
    monkeypatch.setattr(reranker, "_get_ranker", lambda: ranker)

    results = reranker.rerank_candidates("database timeout", candidates, limit=1)

    assert [result.source_id for result in results] == ["second"]
    assert results[0].score == 0.91
    assert results[0].rrf_score == 0.029
    assert results[0].semantic_score == 0.8
    assert results[0].lexical_score == 4.0


def test_rerank_candidates_handles_empty_candidates_without_loading_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def get_ranker() -> None:
        pytest.fail("ranker should not load")

    monkeypatch.setattr(reranker, "_get_ranker", get_ranker)

    assert reranker.rerank_candidates("timeout", []) == []


def test_rerank_candidates_rejects_invalid_input() -> None:
    with pytest.raises(ValueError, match="empty"):
        reranker.rerank_candidates("   ", [])
    with pytest.raises(ValueError, match="Limit"):
        reranker.rerank_candidates("timeout", [], limit=0)


def _candidate(source_id: str, score: float) -> HybridSearchResult:
    return HybridSearchResult(
        score=score,
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
