from __future__ import annotations

import uuid
from dataclasses import dataclass

from qdrant_client import models

from app.retrieval.diff_indexer import DIFF_COLLECTION_NAME
from app.retrieval.embeddings import embed_query
from app.retrieval.vector_store import ensure_collection, get_qdrant_client


@dataclass(frozen=True, slots=True)
class DiffSearchResult:
    score: float
    repository_id: str
    pull_request_number: int
    file_path: str
    status: str
    sha: str
    hunk_header: str
    hunk_index: int
    text: str
    blob_url: str


async def search_diff_hunks(
    repository_id: uuid.UUID,
    query: str,
    limit: int = 10,
    minimum_score: float | None = None,
) -> list[DiffSearchResult]:
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("Query cannot be empty.")

    client = get_qdrant_client()

    try:
        await ensure_collection(client, collection_name=DIFF_COLLECTION_NAME)
        response = await client.query_points(
            collection_name=DIFF_COLLECTION_NAME,
            query=embed_query(cleaned_query),
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

        return [_result_from_point(point) for point in response.points]
    finally:
        await client.close()


def _result_from_point(point: models.ScoredPoint) -> DiffSearchResult:
    payload = point.payload or {}
    return DiffSearchResult(
        score=point.score,
        repository_id=str(payload["repository_id"]),
        pull_request_number=int(payload["pull_request_number"]),
        file_path=str(payload["file_path"]),
        status=str(payload["status"]),
        sha=str(payload["sha"]),
        hunk_header=str(payload["hunk_header"]),
        hunk_index=int(payload["hunk_index"]),
        text=str(payload["text"]),
        blob_url=str(payload["blob_url"]),
    )
