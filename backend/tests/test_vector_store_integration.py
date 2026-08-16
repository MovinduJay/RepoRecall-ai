import uuid

import pytest
from qdrant_client import models

from app.retrieval import vector_store

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_semantic_search_does_not_cross_repository_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collection_name = f"test_repository_filter_{uuid.uuid4().hex}"
    repository_a = uuid.uuid4()
    repository_b = uuid.uuid4()
    query_vector = [1.0] + [0.0] * (vector_store.VECTOR_SIZE - 1)

    monkeypatch.setattr(vector_store, "COLLECTION_NAME", collection_name)
    monkeypatch.setattr(vector_store, "embed_query", lambda query: query_vector)

    client = vector_store.get_qdrant_client()

    try:
        await vector_store.ensure_collection(client)
        await client.upsert(
            collection_name=collection_name,
            points=[
                _point_for_repository(repository_a, query_vector, "Repository A issue"),
                _point_for_repository(repository_b, query_vector, "Repository B issue"),
            ],
            wait=True,
        )

        results = await vector_store.search_similar(
            repository_id=repository_a,
            query="database connections exhausted",
            limit=10,
        )

        assert len(results) == 1
        assert results[0].repository_id == str(repository_a)
        assert results[0].title == "Repository A issue"
    finally:
        if await client.collection_exists(collection_name=collection_name):
            await client.delete_collection(collection_name=collection_name)
        await client.close()


@pytest.mark.asyncio
async def test_semantic_search_applies_minimum_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collection_name = f"test_minimum_score_{uuid.uuid4().hex}"
    repository_id = uuid.uuid4()
    query_vector = [1.0] + [0.0] * (vector_store.VECTOR_SIZE - 1)
    unrelated_vector = [0.0, 1.0] + [0.0] * (vector_store.VECTOR_SIZE - 2)

    monkeypatch.setattr(vector_store, "COLLECTION_NAME", collection_name)
    monkeypatch.setattr(vector_store, "embed_query", lambda query: query_vector)

    client = vector_store.get_qdrant_client()

    try:
        await vector_store.ensure_collection(client)
        await client.upsert(
            collection_name=collection_name,
            points=[
                _point_for_repository(repository_id, query_vector, "Relevant issue"),
                _point_for_repository(repository_id, unrelated_vector, "Unrelated issue"),
            ],
            wait=True,
        )

        results = await vector_store.search_similar(
            repository_id=repository_id,
            query="database connections exhausted",
            limit=10,
            minimum_score=0.5,
        )

        assert [result.title for result in results] == ["Relevant issue"]
        assert results[0].score >= 0.5
    finally:
        if await client.collection_exists(collection_name=collection_name):
            await client.delete_collection(collection_name=collection_name)
        await client.close()


def _point_for_repository(
    repository_id: uuid.UUID,
    vector: list[float],
    title: str,
) -> models.PointStruct:
    raw_document_id = uuid.uuid4()

    return models.PointStruct(
        id=str(uuid.uuid4()),
        vector=vector,
        payload={
            "raw_document_id": str(raw_document_id),
            "repository_id": str(repository_id),
            "source_type": "issue",
            "source_id": str(raw_document_id),
            "source_number": 1,
            "title": title,
            "text": "The PostgreSQL connection pool was exhausted.",
            "html_url": "https://github.com/example/repository/issues/1",
            "chunk_index": 0,
        },
    )
