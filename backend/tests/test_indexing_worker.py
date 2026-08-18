from unittest.mock import AsyncMock

import pytest

from app.workers import indexing_worker


@pytest.mark.asyncio
async def test_fetch_pull_request_files_limits_pr_fan_out() -> None:
    client = AsyncMock()
    client.list_pull_request_files.side_effect = [
        [_github_file(index)] for index in range(indexing_worker.PULL_REQUESTS_WITH_FILES_LIMIT)
    ]
    pull_requests = [
        {"number": number}
        for number in range(1, indexing_worker.PULL_REQUESTS_WITH_FILES_LIMIT + 3)
    ]

    files = await indexing_worker._fetch_pull_request_files(
        client=client,
        owner="acme",
        name="billing",
        pull_requests=pull_requests,
    )

    assert len(files) == indexing_worker.PULL_REQUESTS_WITH_FILES_LIMIT
    assert (
        client.list_pull_request_files.await_count
        == indexing_worker.PULL_REQUESTS_WITH_FILES_LIMIT
    )
    assert files[0].pull_request_number == 1
    assert files[-1].pull_request_number == indexing_worker.PULL_REQUESTS_WITH_FILES_LIMIT
    client.list_pull_request_files.assert_any_await(
        owner="acme",
        name="billing",
        pull_request_number=1,
        max_items=indexing_worker.FILES_PER_PULL_REQUEST_LIMIT,
    )


@pytest.mark.asyncio
async def test_fetch_commit_files_limits_commit_fan_out() -> None:
    client = AsyncMock()
    client.list_commit_files.side_effect = [
        [_github_file(index)] for index in range(indexing_worker.COMMITS_WITH_FILES_LIMIT)
    ]
    commits = [
        {"sha": f"commit-{number}"}
        for number in range(1, indexing_worker.COMMITS_WITH_FILES_LIMIT + 3)
    ]

    files = await indexing_worker._fetch_commit_files(
        client=client,
        owner="acme",
        name="billing",
        commits=commits,
    )

    assert len(files) == indexing_worker.COMMITS_WITH_FILES_LIMIT
    assert client.list_commit_files.await_count == indexing_worker.COMMITS_WITH_FILES_LIMIT
    assert files[0].commit_sha == "commit-1"
    assert files[-1].commit_sha == f"commit-{indexing_worker.COMMITS_WITH_FILES_LIMIT}"
    client.list_commit_files.assert_any_await(
        owner="acme",
        name="billing",
        commit_sha="commit-1",
        max_items=indexing_worker.FILES_PER_COMMIT_LIMIT,
    )


def _github_file(index: int) -> dict:
    return {
        "sha": f"sha-{index}",
        "filename": f"app/file_{index}.py",
        "status": "modified",
        "additions": 2,
        "deletions": 1,
        "changes": 3,
        "patch": "@@ -1 +1 @@\n-old\n+new",
        "blob_url": f"https://github.com/acme/billing/blob/sha/app/file_{index}.py",
        "raw_url": f"https://github.com/acme/billing/raw/sha/app/file_{index}.py",
        "contents_url": (
            f"https://api.github.com/repos/acme/billing/contents/app/file_{index}.py"
        ),
    }
