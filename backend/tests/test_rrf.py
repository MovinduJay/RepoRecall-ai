from app.retrieval.rrf import reciprocal_rank_fusion
from app.retrieval.vector_store import SemanticSearchResult


def test_rrf_rewards_chunks_found_by_both_retrievers() -> None:
    semantic = [_result("semantic-only", 0.95), _result("shared", 0.70)]
    lexical = [_result("lexical-only", 8.4), _result("shared", 4.2)]

    results = reciprocal_rank_fusion(semantic, lexical, rank_constant=60)

    assert [result.source_id for result in results] == [
        "shared",
        "lexical-only",
        "semantic-only",
    ]
    assert results[0].score == 2 / 62
    assert results[0].semantic_score == 0.70
    assert results[0].lexical_score == 4.2


def test_rrf_uses_rank_not_incomparable_source_scores() -> None:
    semantic = [_result("semantic-first", 0.51)]
    lexical = [_result("lexical-first", 100.0)]

    results = reciprocal_rank_fusion(semantic, lexical)

    assert results[0].score == results[1].score
    assert {result.source_id for result in results} == {"semantic-first", "lexical-first"}


def test_rrf_applies_limit_and_keeps_missing_scores_explicit() -> None:
    results = reciprocal_rank_fusion(
        [_result("semantic-only", 0.9)],
        [_result("lexical-only", 3.1)],
        limit=1,
    )

    assert len(results) == 1
    assert (results[0].semantic_score is None) != (results[0].lexical_score is None)


def _result(source_id: str, score: float) -> SemanticSearchResult:
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
