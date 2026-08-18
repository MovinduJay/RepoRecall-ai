import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.routes import search
from app.main import app
from app.retrieval.lexical_search import LexicalSearchResult


def test_lexical_search_returns_structured_results() -> None:
    repository_id = uuid.uuid4()
    search_lexically = AsyncMock(
        return_value=[
            LexicalSearchResult(
                score=2.45,
                raw_document_id=str(uuid.uuid4()),
                repository_id=str(repository_id),
                source_type="issue",
                source_id="123",
                source_number=123,
                title="Consumer closes unexpectedly",
                text="InvoiceConsumer.java raised AlreadyClosedException.",
                html_url="https://github.com/acme/repo/issues/123",
                chunk_index=0,
            )
        ]
    )
    original_search = search.search_lexically
    search.search_lexically = search_lexically

    try:
        response = TestClient(app).post(
            "/api/v1/search/lexical",
            json={
                "repository_id": str(repository_id),
                "query": "  AlreadyClosedException  ",
                "limit": 5,
            },
        )
    finally:
        search.search_lexically = original_search

    assert response.status_code == 200
    assert response.json()["query"] == "AlreadyClosedException"
    assert response.json()["results"][0]["source_number"] == 123
    assert response.json()["results"][0]["score"] == 2.45
    search_lexically.assert_awaited_once_with(
        repository_id=repository_id,
        query="AlreadyClosedException",
        limit=5,
    )


def test_lexical_search_rejects_blank_query_and_invalid_limit() -> None:
    client = TestClient(app)
    repository_id = str(uuid.uuid4())

    blank_response = client.post(
        "/api/v1/search/lexical",
        json={"repository_id": repository_id, "query": "   "},
    )
    invalid_limit_response = client.post(
        "/api/v1/search/lexical",
        json={"repository_id": repository_id, "query": "timeout", "limit": 51},
    )

    assert blank_response.status_code == 422
    assert invalid_limit_response.status_code == 422
