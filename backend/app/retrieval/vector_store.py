from __future__ import annotations

import os
import uuid

from qdrant_client import AsyncQdrantClient, models

from app.retrieval.embeddings import embed_passage, embed_query

COLLECTION_NAME = "github_chunks"
VECTOR_SIZE = 384

QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://qdrant:6333",
)

DEMO_DOCUMENTS = [
    {
        "source_id": "issue-101",
        "text": "RabbitMQ redelivery created duplicate invoices.",
        "source_type": "issue",
        "title": "Duplicate invoice processing",
    },
    {
        "source_id": "issue-102",
        "text": "Expired JWT access tokens caused users to be logged out.",
        "source_type": "issue",
        "title": "Unexpected user logout",
    },
    {
        "source_id": "issue-103",
        "text": "The PostgreSQL connection pool was exhausted during high traffic.",
        "source_type": "issue",
        "title": "Database connections unavailable",
    },
]

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


async def store_sample_point() -> str:
    """
    Create one embedding and store it in Qdrant.
    """

    client = get_qdrant_client()

    try:
        await ensure_collection(client)

        text = "RabbitMQ redelivery created duplicate invoices."

        vector = embed_passage(text)

        point_id = str(uuid.uuid4())

        await client.upsert(
            collection_name=COLLECTION_NAME,
            wait=True,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "text": text,
                        "source_type": "issue",
                        "title": "Duplicate invoice processing",
                        "repository": "example/billing-service",
                    },
                )
            ],
        )

        return point_id

    finally:
        await client.close()
        
        
async def store_demo_points() -> int:
    """
    Embed and store several example GitHub documents.
    """

    client = get_qdrant_client()

    try:
        await ensure_collection(client)

        points: list[models.PointStruct] = []

        for document in DEMO_DOCUMENTS:
            vector = embed_passage(document["text"])

            # uuid5 produces the same UUID for the same source ID.
            # Running this function again updates the point instead of duplicating it.
            point_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"reporecall:{document['source_id']}",
                )
            )

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=document,
                )
            )

        await client.upsert(
            collection_name=COLLECTION_NAME,
            wait=True,
            points=points,
        )

        return len(points)

    finally:
        await client.close()       
        
        
        
async def search_similar(
    query: str,
    limit: int = 3,
) -> list[dict[str, object]]:
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
            limit=limit,
            with_payload=True,
        )

        results: list[dict[str, object]] = []

        for point in response.points:
            payload = point.payload or {}

            results.append(
                {
                    "score": point.score,
                    "source_id": payload.get("source_id"),
                    "title": payload.get("title"),
                    "text": payload.get("text"),
                }
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