import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.routes import search
from app.main import app
from app.retrieval.vector_store import SemanticSearchResult


def test_semantic_search_returns_structured_results() -> None:
    repository_id = uuid.uuid4()
    search_similar = AsyncMock(
        return_value=[
            SemanticSearchResult(
                score=0.82,
                raw_document_id=str(uuid.uuid4()),
                repository_id=str(repository_id),
                source_type="issue",
                source_id="123",
                source_number=123,
                title="Database connections unavailable",
                text="The PostgreSQL connection pool was exhausted.",
                html_url="https://github.com/example/repository/issues/123",
                chunk_index=0,
            )
        ]
    )
    original_search_similar = search.search_similar
    search.search_similar = search_similar

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/search/semantic",
                json={
                    "repository_id": str(repository_id),
                    "query": "  database connections exhausted  ",
                    "limit": 5,
                    "minimum_score": 0.7,
                },
            )
    finally:
        search.search_similar = original_search_similar

    assert response.status_code == 200
    assert response.json()["query"] == "database connections exhausted"
    assert response.json()["results"][0]["source_number"] == 123
    search_similar.assert_awaited_once_with(
        repository_id=repository_id,
        query="database connections exhausted",
        limit=5,
        minimum_score=0.7,
    )


def test_semantic_search_rejects_blank_query() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/search/semantic",
            json={"repository_id": str(uuid.uuid4()), "query": "   "},
        )

    assert response.status_code == 422


def test_semantic_search_rejects_invalid_limits_and_scores() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/search/semantic",
            json={
                "repository_id": str(uuid.uuid4()),
                "query": "connection failure",
                "limit": 0,
                "minimum_score": 1.1,
            },
        )

    assert response.status_code == 422
