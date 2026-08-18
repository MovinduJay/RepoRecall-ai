import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.retrieval import lexical_search


@pytest.mark.asyncio
async def test_search_lexically_pages_repository_chunks_and_returns_bm25_ranking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_id = uuid.uuid4()
    client = AsyncMock()
    client.scroll.side_effect = [
        (
            [
                _record(
                    point_id="11111111-1111-1111-1111-111111111111",
                    repository_id=repository_id,
                    source_id="generic",
                    text="The message consumer stopped after reconnecting.",
                )
            ],
            "next-page",
        ),
        (
            [
                _record(
                    point_id="22222222-2222-2222-2222-222222222222",
                    repository_id=repository_id,
                    source_id="exact",
                    text="InvoiceConsumer.java raised AlreadyClosedException.",
                )
            ],
            None,
        ),
    ]
    monkeypatch.setattr(lexical_search, "get_qdrant_client", lambda: client)
    monkeypatch.setattr(lexical_search, "ensure_collection", AsyncMock())

    results = await lexical_search.search_lexically(
        repository_id=repository_id,
        query="AlreadyClosedException InvoiceConsumer.java",
        limit=5,
    )

    assert [result.source_id for result in results] == ["exact"]
    assert results[0].repository_id == str(repository_id)
    assert client.scroll.await_count == 2
    first_call = client.scroll.await_args_list[0].kwargs
    assert first_call["scroll_filter"].must[0].match.value == str(repository_id)
    assert first_call["with_vectors"] is False
    assert client.scroll.await_args_list[1].kwargs["offset"] == "next-page"
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_lexically_rejects_query_without_tokens() -> None:
    with pytest.raises(ValueError, match="searchable token"):
        await lexical_search.search_lexically(uuid.uuid4(), "()")


def _record(
    *,
    point_id: str,
    repository_id: uuid.UUID,
    source_id: str,
    text: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=point_id,
        payload={
            "raw_document_id": str(uuid.uuid4()),
            "repository_id": str(repository_id),
            "source_type": "issue",
            "source_id": source_id,
            "source_number": 10,
            "title": source_id,
            "text": text,
            "html_url": f"https://github.com/acme/repo/issues/{source_id}",
            "chunk_index": 0,
        },
    )
