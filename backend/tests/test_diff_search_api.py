import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.routes import search
from app.main import app
from app.retrieval.diff_search import DiffSearchResult


def test_diff_search_returns_structured_results() -> None:
    repository_id = uuid.uuid4()
    search_diff_hunks = AsyncMock(
        return_value=[
            DiffSearchResult(
                score=0.86,
                repository_id=str(repository_id),
                pull_request_number=14,
                file_path="app/consumer.py",
                status="modified",
                sha="abc123",
                hunk_header="@@ -20,2 +20,3 @@ def process():",
                hunk_index=0,
                text="-acknowledge()\n+commit()\n+acknowledge()",
                blob_url="https://github.com/acme/billing/blob/abc123/app/consumer.py",
            )
        ]
    )
    original_search = search.search_diff_hunks
    search.search_diff_hunks = search_diff_hunks

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/search/diffs",
                json={
                    "repository_id": str(repository_id),
                    "query": " acknowledge after commit ",
                    "limit": 5,
                    "minimum_score": 0.7,
                },
            )
    finally:
        search.search_diff_hunks = original_search

    assert response.status_code == 200
    assert response.json()["query"] == "acknowledge after commit"
    assert response.json()["results"][0]["file_path"] == "app/consumer.py"
    search_diff_hunks.assert_awaited_once_with(
        repository_id=repository_id,
        query="acknowledge after commit",
        limit=5,
        minimum_score=0.7,
    )
