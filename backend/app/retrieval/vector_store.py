from __future__ import annotations

import os
import uuid

from qdrant_client import AsyncQdrantClient, models

from app.retrieval.embeddings import embed_passage


COLLECTION_NAME = "github_chunks"
VECTOR_SIZE = 384

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