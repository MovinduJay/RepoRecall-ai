import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.routes import search
from app.main import app
from app.retrieval.rrf import HybridSearchResult


def test_hybrid_search_returns_fused_scores() -> None:
    repository_id = uuid.uuid4()
    search_hybrid = AsyncMock(
        return_value=[
            HybridSearchResult(
                score=0.032,
                semantic_score=0.82,
                lexical_score=4.1,
                raw_document_id=str(uuid.uuid4()),
                repository_id=str(repository_id),
                source_type="issue",
                source_id="123",
                source_number=123,
                title="Database timeout",
                text="The connection pool was exhausted.",
                html_url="https://github.com/acme/repo/issues/123",
                chunk_index=0,
            )
        ]
    )
    original_search = search.search_hybrid
    search.search_hybrid = search_hybrid

    try:
        response = TestClient(app).post(
            "/api/v1/search/hybrid",
            json={
                "repository_id": str(repository_id),
                "query": "  database timeout  ",
                "limit": 5,
            },
        )
    finally:
        search.search_hybrid = original_search

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["score"] == 0.032
    assert result["semantic_score"] == 0.82
    assert result["lexical_score"] == 4.1
    search_hybrid.assert_awaited_once_with(
        repository_id=repository_id,
        query="database timeout",
        limit=5,
    )
