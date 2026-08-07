from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient, models

from app.retrieval.embeddings import embed_query

COLLECTION_NAME = "github_chunks"
VECTOR_SIZE = 384


@dataclass(frozen=True)
class SemanticSearchResult:
    score: float
    raw_document_id: str
    repository_id: str
    source_type: str
    source_id: str
    source_number: int | None
    title: str
    text: str
    html_url: str
    chunk_index: int


QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://qdrant:6333",
)


def get_qdrant_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(url=QDRANT_URL)


async def ensure_collection(
    client: AsyncQdrantClient,
) -> None:
    """
    Create the collection only when it does not already exist.
    """

    exists = await client.collection_exists(
        collection_name=COLLECTION_NAME
    )

    if exists:
        return

    await client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE,
        ),
    )


async def search_similar(
    repository_id: uuid.UUID,
    query: str,
    limit: int = 10,
    minimum_score: float | None = None,
) -> list[SemanticSearchResult]:
    """
    Find stored documents whose meaning is similar to the query.
    """

    cleaned_query = query.strip()

    if not cleaned_query:
        raise ValueError("Query cannot be empty.")

    client = get_qdrant_client()

    try:
        await ensure_collection(client)

        query_vector = embed_query(cleaned_query)

        response = await client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="repository_id",
                        match=models.MatchValue(value=str(repository_id)),
                    )
                ]
            ),
            limit=limit,
            score_threshold=minimum_score,
            with_payload=True,
        )

        results: list[SemanticSearchResult] = []

        for point in response.points:
            payload = point.payload or {}

            results.append(
                SemanticSearchResult(
                    score=point.score,
                    raw_document_id=str(payload["raw_document_id"]),
                    repository_id=str(payload["repository_id"]),
                    source_type=str(payload["source_type"]),
                    source_id=str(payload["source_id"]),
                    source_number=payload.get("source_number"),
                    title=str(payload["title"]),
                    text=str(payload["text"]),
                    html_url=str(payload["html_url"]),
                    chunk_index=int(payload["chunk_index"]),
                )
            )

        return results

    finally:
        await client.close()
        
async def reset_collection() -> None:
    """
    Delete the current Qdrant collection and recreate it empty.

    Warning: this removes every vector currently stored
    in the github_chunks collection.
    """

    client = get_qdrant_client()

    try:
        exists = await client.collection_exists(
            collection_name=COLLECTION_NAME,
        )

        if exists:
            await client.delete_collection(
                collection_name=COLLECTION_NAME,
            )

        await ensure_collection(client)

    finally:
        await client.close()
