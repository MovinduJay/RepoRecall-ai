from __future__ import annotations

import uuid

from qdrant_client import AsyncQdrantClient, models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pull_request_file import PullRequestFile
from app.retrieval.diff_chunking import DiffChunk, chunk_pull_request_file
from app.retrieval.embeddings import embed_passages
from app.retrieval.indexer import EMBEDDING_BATCH_SIZE
from app.retrieval.vector_store import ensure_collection, get_qdrant_client

DIFF_COLLECTION_NAME = "github_diff_chunks"


async def index_repository_diffs(
    session: AsyncSession,
    repository_id: uuid.UUID,
) -> dict[str, int]:
    result = await session.execute(
        select(PullRequestFile)
        .where(PullRequestFile.repository_id == repository_id)
        .order_by(PullRequestFile.ingested_at.asc())
    )
    files = list(result.scalars().all())
    chunks = [chunk for file in files for chunk in chunk_pull_request_file(file)]

    client = get_qdrant_client()

    try:
        await ensure_collection(client, collection_name=DIFF_COLLECTION_NAME)
        chunks_indexed = 0
        current_point_ids: set[str] = set()

        for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
            batch_chunks = chunks[start : start + EMBEDDING_BATCH_SIZE]
            vectors = embed_passages([chunk.text for chunk in batch_chunks])
            points: list[models.PointStruct] = []

            for chunk, vector in zip(batch_chunks, vectors, strict=True):
                point_id = _create_diff_point_id(repository_id, chunk)
                current_point_ids.add(point_id)
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            **chunk.metadata,
                            "repository_id": str(repository_id),
                            "source_type": "pull_request_file_diff",
                            "text": chunk.text,
                        },
                    )
                )

            await client.upsert(
                collection_name=DIFF_COLLECTION_NAME,
                points=points,
                wait=True,
            )
            chunks_indexed += len(points)

        chunks_deleted = await _delete_stale_diff_points(
            client=client,
            repository_id=repository_id,
            current_point_ids=current_point_ids,
        )

        return {
            "files_loaded": len(files),
            "chunks_indexed": chunks_indexed,
            "chunks_deleted": chunks_deleted,
        }
    finally:
        await client.close()


def _create_diff_point_id(repository_id: uuid.UUID, chunk: DiffChunk) -> str:
    stable_key = (
        f"reporecall-diff:{repository_id}:{chunk.pull_request_number}:"
        f"{chunk.file_path}:{chunk.hunk_index}"
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, stable_key))


async def _delete_stale_diff_points(
    *,
    client: AsyncQdrantClient,
    repository_id: uuid.UUID,
    current_point_ids: set[str],
) -> int:
    stale_point_ids: list[str | int | uuid.UUID] = []
    offset: int | str | uuid.UUID | None = None
    repository_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="repository_id",
                match=models.MatchValue(value=str(repository_id)),
            )
        ]
    )

    while True:
        records, next_offset = await client.scroll(
            collection_name=DIFF_COLLECTION_NAME,
            scroll_filter=repository_filter,
            limit=256,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        stale_point_ids.extend(
            record.id for record in records if str(record.id) not in current_point_ids
        )

        if next_offset is None:
            break
        offset = next_offset

    if stale_point_ids:
        await client.delete(
            collection_name=DIFF_COLLECTION_NAME,
            points_selector=models.PointIdsList(points=stale_point_ids),
            wait=True,
        )

    return len(stale_point_ids)
