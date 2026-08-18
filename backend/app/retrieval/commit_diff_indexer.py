from __future__ import annotations

import uuid

from qdrant_client import models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commit_file import CommitFile
from app.retrieval.commit_diff_chunking import CommitDiffChunk, chunk_commit_file
from app.retrieval.diff_indexer import _delete_stale_diff_points
from app.retrieval.embeddings import embed_passages
from app.retrieval.indexer import EMBEDDING_BATCH_SIZE
from app.retrieval.vector_store import ensure_collection, get_qdrant_client

COMMIT_DIFF_COLLECTION_NAME = "github_commit_diff_chunks"


async def index_repository_commit_diffs(
    session: AsyncSession,
    repository_id: uuid.UUID,
) -> dict[str, int]:
    result = await session.execute(
        select(CommitFile)
        .where(CommitFile.repository_id == repository_id)
        .order_by(CommitFile.ingested_at.asc())
    )
    files = list(result.scalars().all())
    chunks = [chunk for file in files for chunk in chunk_commit_file(file)]
    client = get_qdrant_client()

    try:
        await ensure_collection(client, collection_name=COMMIT_DIFF_COLLECTION_NAME)
        chunks_indexed = 0
        current_point_ids: set[str] = set()

        for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
            batch_chunks = chunks[start : start + EMBEDDING_BATCH_SIZE]
            vectors = embed_passages([chunk.text for chunk in batch_chunks])
            points: list[models.PointStruct] = []

            for chunk, vector in zip(batch_chunks, vectors, strict=True):
                point_id = _create_commit_diff_point_id(repository_id, chunk)
                current_point_ids.add(point_id)
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            **chunk.metadata,
                            "repository_id": str(repository_id),
                            "source_type": "commit_file_diff",
                            "text": chunk.text,
                        },
                    )
                )

            await client.upsert(
                collection_name=COMMIT_DIFF_COLLECTION_NAME,
                points=points,
                wait=True,
            )
            chunks_indexed += len(points)

        chunks_deleted = await _delete_stale_diff_points(
            client=client,
            repository_id=repository_id,
            current_point_ids=current_point_ids,
            collection_name=COMMIT_DIFF_COLLECTION_NAME,
        )
        return {
            "files_loaded": len(files),
            "chunks_indexed": chunks_indexed,
            "chunks_deleted": chunks_deleted,
        }
    finally:
        await client.close()


def _create_commit_diff_point_id(
    repository_id: uuid.UUID,
    chunk: CommitDiffChunk,
) -> str:
    stable_key = (
        f"reporecall-commit-diff:{repository_id}:{chunk.commit_sha}:"
        f"{chunk.file_path}:{chunk.hunk_index}"
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, stable_key))
