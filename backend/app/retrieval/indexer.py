from __future__ import annotations

import uuid

from qdrant_client import models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_document import RawDocument
from app.retrieval.chunking import DocumentChunk, chunk_raw_document
from app.retrieval.embeddings import embed_passages
from app.retrieval.vector_store import (
    COLLECTION_NAME,
    ensure_collection,
    get_qdrant_client,
)


EMBEDDING_BATCH_SIZE = 16


async def index_repository_documents(
    session: AsyncSession,
    repository_id: uuid.UUID,
) -> dict[str, int]:
    """
    Load a repository's GitHub documents from PostgreSQL,
    split them into chunks, generate embeddings, and store
    the resulting vectors in Qdrant.
    """

    # Step 1: Load real GitHub documents from PostgreSQL.
    result = await session.execute(
        select(RawDocument)
        .where(RawDocument.repository_id == repository_id)
        .order_by(RawDocument.ingested_at.asc())
    )

    documents = list(result.scalars().all())

    print(
        f"Loaded {len(documents)} raw documents.",
        flush=True,
    )

    # Step 2: Convert every raw document into smaller chunks.
    chunks: list[DocumentChunk] = []

    for document in documents:
        document_chunks = chunk_raw_document(document)
        chunks.extend(document_chunks)

    print(
        f"Created {len(chunks)} chunks.",
        flush=True,
    )

    if not chunks:
        return {
            "documents_loaded": len(documents),
            "chunks_indexed": 0,
        }

    # Step 3: Connect to Qdrant and make sure the collection exists.
    client = get_qdrant_client()

    try:
        await ensure_collection(client)

        chunks_indexed = 0

        total_batches = (
            len(chunks) + EMBEDDING_BATCH_SIZE - 1
        ) // EMBEDDING_BATCH_SIZE

        # Step 4: Process chunks in small batches.
        for start in range(
            0,
            len(chunks),
            EMBEDDING_BATCH_SIZE,
        ):
            batch_chunks = chunks[
                start : start + EMBEDDING_BATCH_SIZE
            ]

            batch_number = (
                start // EMBEDDING_BATCH_SIZE
            ) + 1

            print(
                f"Embedding batch {batch_number}/{total_batches} "
                f"({len(batch_chunks)} chunks)...",
                flush=True,
            )

            # Extract text from the current batch.
            texts = [
                chunk.text
                for chunk in batch_chunks
            ]

            # Convert all texts in this batch into vectors.
            vectors = embed_passages(texts)

            points: list[models.PointStruct] = []

            # Step 5: Combine every vector with its metadata.
            for chunk, vector in zip(
                batch_chunks,
                vectors,
                strict=True,
            ):
                point_id = _create_point_id(chunk)

                payload = {
                    **chunk.metadata,
                    "raw_document_id": chunk.raw_document_id,
                    "text": chunk.text,
                }

                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload,
                    )
                )

            # Step 6: Store this batch in Qdrant.
            await client.upsert(
                collection_name=COLLECTION_NAME,
                points=points,
                wait=True,
            )

            chunks_indexed += len(points)

            print(
                f"Indexed {chunks_indexed}/{len(chunks)} chunks.",
                flush=True,
            )

        return {
            "documents_loaded": len(documents),
            "chunks_indexed": chunks_indexed,
        }

    finally:
        await client.close()


def _create_point_id(
    chunk: DocumentChunk,
) -> str:
    """
    Generate a stable Qdrant point ID.

    The same raw document and chunk index always produce
    the same UUID. This prevents duplicate vectors when
    indexing is run more than once.
    """

    stable_key = (
        f"reporecall:"
        f"{chunk.raw_document_id}:"
        f"{chunk.chunk_index}"
    )

    point_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        stable_key,
    )

    return str(point_id)