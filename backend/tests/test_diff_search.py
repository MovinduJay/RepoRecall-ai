import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.retrieval import diff_search


@pytest.mark.asyncio
async def test_search_diff_hunks_filters_repository_and_maps_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_id = uuid.uuid4()
    client = AsyncMock()
    client.query_points.return_value = SimpleNamespace(
        points=[
            SimpleNamespace(
                score=0.86,
                payload={
                    "repository_id": str(repository_id),
                    "pull_request_number": 14,
                    "file_path": "app/consumer.py",
                    "status": "modified",
                    "sha": "abc123",
                    "hunk_header": "@@ -20,2 +20,3 @@ def process():",
                    "hunk_index": 0,
                    "text": "-acknowledge()\n+commit()\n+acknowledge()",
                    "blob_url": "https://github.com/acme/billing/blob/abc123/app/consumer.py",
                },
            )
        ]
    )
    monkeypatch.setattr(diff_search, "get_qdrant_client", lambda: client)
    monkeypatch.setattr(diff_search, "ensure_collection", AsyncMock())
    monkeypatch.setattr(diff_search, "embed_query", lambda query: [0.1, 0.2])

    results = await diff_search.search_diff_hunks(
        repository_id=repository_id,
        query="acknowledge after commit",
        limit=5,
        minimum_score=0.7,
    )

    query_arguments = client.query_points.await_args.kwargs
    assert query_arguments["collection_name"] == diff_search.DIFF_COLLECTION_NAME
    assert query_arguments["query_filter"].must[0].match.value == str(repository_id)
    assert query_arguments["score_threshold"] == 0.7
    assert results[0].pull_request_number == 14
    assert results[0].file_path == "app/consumer.py"
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_diff_hunks_rejects_empty_query() -> None:
    with pytest.raises(ValueError, match="Query cannot be empty"):
        await diff_search.search_diff_hunks(repository_id=uuid.uuid4(), query="   ")
