import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.retrieval import vector_store


@pytest.mark.asyncio
async def test_ensure_collection_creates_collection_and_repository_index() -> None:
    client = AsyncMock()
    client.collection_exists.return_value = False

    await vector_store.ensure_collection(client)

    client.create_collection.assert_awaited_once()
    collection_arguments = client.create_collection.await_args.kwargs
    vector_parameters = collection_arguments["vectors_config"]
    assert collection_arguments["collection_name"] == vector_store.COLLECTION_NAME
    assert vector_parameters.size == vector_store.VECTOR_SIZE
    assert vector_parameters.distance == vector_store.models.Distance.COSINE
    client.create_payload_index.assert_awaited_once_with(
        collection_name=vector_store.COLLECTION_NAME,
        field_name="repository_id",
        field_schema=vector_store.models.PayloadSchemaType.KEYWORD,
        wait=True,
    )


@pytest.mark.asyncio
async def test_ensure_collection_indexes_existing_collection() -> None:
    client = AsyncMock()
    client.collection_exists.return_value = True

    await vector_store.ensure_collection(client)

    client.create_collection.assert_not_awaited()
    client.create_payload_index.assert_awaited_once_with(
        collection_name=vector_store.COLLECTION_NAME,
        field_name="repository_id",
        field_schema=vector_store.models.PayloadSchemaType.KEYWORD,
        wait=True,
    )


@pytest.mark.asyncio
async def test_search_similar_filters_repository_and_returns_structured_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_id = uuid.uuid4()
    raw_document_id = uuid.uuid4()
    client = AsyncMock()
    client.query_points.return_value = SimpleNamespace(
        points=[
            SimpleNamespace(
                score=0.82,
                payload={
                    "raw_document_id": str(raw_document_id),
                    "repository_id": str(repository_id),
                    "source_type": "issue",
                    "source_id": "123",
                    "source_number": 123,
                    "title": "Database connections unavailable",
                    "text": "The PostgreSQL connection pool was exhausted.",
                    "html_url": "https://github.com/example/repository/issues/123",
                    "chunk_index": 0,
                },
            )
        ]
    )
    monkeypatch.setattr(vector_store, "get_qdrant_client", lambda: client)
    monkeypatch.setattr(vector_store, "ensure_collection", AsyncMock())
    monkeypatch.setattr(vector_store, "embed_query", lambda query: [0.1, 0.2])

    results = await vector_store.search_similar(
        repository_id=repository_id,
        query="database connections exhausted",
        limit=5,
        minimum_score=0.7,
    )

    query_arguments = client.query_points.await_args.kwargs
    repository_condition = query_arguments["query_filter"].must[0]
    assert repository_condition.key == "repository_id"
    assert repository_condition.match.value == str(repository_id)
    assert query_arguments["score_threshold"] == 0.7
    assert results == [
        vector_store.SemanticSearchResult(
            score=0.82,
            raw_document_id=str(raw_document_id),
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
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_similar_rejects_empty_query() -> None:
    with pytest.raises(ValueError, match="Query cannot be empty"):
        await vector_store.search_similar(repository_id=uuid.uuid4(), query="   ")
