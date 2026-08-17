import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.ingestion.normalizers import PullRequestFileInput
from app.retrieval.diff_chunking import chunk_pull_request_file
from app.retrieval.diff_indexer import _create_diff_point_id, _delete_stale_diff_points


def test_diff_point_id_is_deterministic() -> None:
    repository_id = uuid.uuid4()
    chunk = chunk_pull_request_file(_file_input())[0]

    first_id = _create_diff_point_id(repository_id, chunk)
    second_id = _create_diff_point_id(repository_id, chunk)

    assert first_id == second_id
    assert uuid.UUID(first_id).version == 5


def test_diff_point_id_changes_for_another_hunk() -> None:
    repository_id = uuid.uuid4()
    chunks = chunk_pull_request_file(_file_input())

    assert _create_diff_point_id(repository_id, chunks[0]) != _create_diff_point_id(
        repository_id, chunks[1]
    )


@pytest.mark.asyncio
async def test_delete_stale_diff_points_keeps_current_repository_points() -> None:
    repository_id = uuid.uuid4()
    current_id = str(uuid.uuid4())
    stale_id = str(uuid.uuid4())
    client = AsyncMock()
    client.scroll.return_value = (
        [SimpleNamespace(id=current_id), SimpleNamespace(id=stale_id)],
        None,
    )

    deleted_count = await _delete_stale_diff_points(
        client=client,
        repository_id=repository_id,
        current_point_ids={current_id},
    )

    assert deleted_count == 1
    delete_arguments = client.delete.await_args.kwargs
    assert delete_arguments["points_selector"].points == [stale_id]
    repository_condition = client.scroll.await_args.kwargs["scroll_filter"].must[0]
    assert repository_condition.match.value == str(repository_id)


def _file_input() -> PullRequestFileInput:
    return PullRequestFileInput(
        pull_request_number=14,
        file_path="app/consumer.py",
        status="modified",
        sha="abc123",
        previous_file_path=None,
        additions=3,
        deletions=1,
        changes=4,
        patch="@@ -1 +1 @@\n-old\n+new\n@@ -10 +10 @@\n-before\n+after",
        blob_url="https://github.com/acme/billing/blob/abc123/app/consumer.py",
        raw_url="https://github.com/acme/billing/raw/abc123/app/consumer.py",
        contents_url="https://api.github.com/repos/acme/billing/contents/app/consumer.py",
        content_hash="a" * 64,
    )
