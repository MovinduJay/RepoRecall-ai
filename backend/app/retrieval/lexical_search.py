from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from qdrant_client import models

from app.retrieval.bm25 import BM25Document, rank_bm25, tokenize
from app.retrieval.vector_store import COLLECTION_NAME, ensure_collection, get_qdrant_client

SCROLL_PAGE_SIZE = 256


@dataclass(frozen=True, slots=True)
class LexicalSearchResult:
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


async def search_lexically(
    repository_id: uuid.UUID,
    query: str,
    limit: int = 10,
) -> list[LexicalSearchResult]:
    """Rank one repository's existing Qdrant chunks with Okapi BM25."""

    cleaned_query = query.strip()
    if not tokenize(cleaned_query):
        raise ValueError("Query must contain at least one searchable token.")

    client = get_qdrant_client()
    try:
        await ensure_collection(client)
        payloads = await _load_repository_payloads(client, repository_id)
        payloads_by_point_id = {point_id: payload for point_id, payload in payloads}
        ranked = rank_bm25(
            cleaned_query,
            (
                BM25Document(document_id=point_id, text=str(payload["text"]))
                for point_id, payload in payloads
            ),
            limit=limit,
        )

        return [
            _to_search_result(item.score, payloads_by_point_id[item.document_id])
            for item in ranked
        ]
    finally:
        await client.close()


async def _load_repository_payloads(
    client: Any,
    repository_id: uuid.UUID,
) -> list[tuple[str, dict[str, Any]]]:
    repository_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="repository_id",
                match=models.MatchValue(value=str(repository_id)),
            )
        ]
    )
    payloads: list[tuple[str, dict[str, Any]]] = []
    offset: int | str | uuid.UUID | None = None

    while True:
        records, next_offset = await client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=repository_filter,
            limit=SCROLL_PAGE_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        payloads.extend(
            (str(record.id), record.payload)
            for record in records
            if record.payload is not None and "text" in record.payload
        )
        if next_offset is None:
            return payloads
        offset = next_offset


def _to_search_result(score: float, payload: dict[str, Any]) -> LexicalSearchResult:
    return LexicalSearchResult(
        score=score,
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
