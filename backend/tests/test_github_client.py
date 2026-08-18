import httpx
import pytest

from app.ingestion.github_client import GitHubApiClient, GitHubRateLimitError


@pytest.mark.asyncio
async def test_list_issues_filters_pull_requests() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["per_page"] == "100"
        return httpx.Response(
            200,
            json=[
                {"id": 1, "number": 1, "title": "Bug"},
                {"id": 2, "number": 2, "title": "PR", "pull_request": {"url": "x"}},
            ],
            request=request,
        )

    async with httpx.AsyncClient(
        base_url="https://api.github.test", transport=httpx.MockTransport(handler)
    ) as http_client:
        client = GitHubApiClient(client=http_client)
        issues = await client.list_issues("owner", "repo", max_items=10)

    assert [issue["id"] for issue in issues] == [1]


@pytest.mark.asyncio
async def test_list_issue_comments_uses_repository_comments_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/owner/repo/issues/comments"
        assert request.url.params["sort"] == "updated"
        assert request.url.params["direction"] == "desc"
        assert request.url.params["per_page"] == "100"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 101,
                    "body": "The transaction must finish before acknowledgement.",
                    "issue_url": "https://api.github.test/repos/owner/repo/issues/12",
                }
            ],
            request=request,
        )

    async with httpx.AsyncClient(
        base_url="https://api.github.test", transport=httpx.MockTransport(handler)
    ) as http_client:
        client = GitHubApiClient(client=http_client)
        comments = await client.list_issue_comments("owner", "repo", max_items=10)

    assert [comment["id"] for comment in comments] == [101]


@pytest.mark.asyncio
async def test_list_review_comments_uses_repository_review_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/owner/repo/pulls/comments"
        assert request.url.params["sort"] == "updated"
        assert request.url.params["direction"] == "desc"
        assert request.url.params["per_page"] == "100"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 201,
                    "body": "Move this acknowledgement after the transaction.",
                    "path": "app/consumer.py",
                }
            ],
            request=request,
        )

    async with httpx.AsyncClient(
        base_url="https://api.github.test", transport=httpx.MockTransport(handler)
    ) as http_client:
        client = GitHubApiClient(client=http_client)
        comments = await client.list_pull_request_review_comments(
            "owner", "repo", max_items=10
        )

    assert [comment["id"] for comment in comments] == [201]


@pytest.mark.asyncio
async def test_list_pull_request_files_uses_numbered_pr_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/owner/repo/pulls/14/files"
        assert request.url.params["per_page"] == "100"
        return httpx.Response(
            200,
            json=[
                {
                    "sha": "abc123",
                    "filename": "app/consumer.py",
                    "status": "modified",
                    "additions": 4,
                    "deletions": 2,
                    "changes": 6,
                    "patch": "@@ -20,2 +20,4 @@",
                }
            ],
            request=request,
        )

    async with httpx.AsyncClient(
        base_url="https://api.github.test", transport=httpx.MockTransport(handler)
    ) as http_client:
        client = GitHubApiClient(client=http_client)
        files = await client.list_pull_request_files(
            "owner", "repo", pull_request_number=14, max_items=10
        )

    assert [file["filename"] for file in files] == ["app/consumer.py"]


@pytest.mark.asyncio
async def test_pagination_stops_at_requested_limit() -> None:
    requested_pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        requested_pages.append(page)
        items = [{"sha": f"sha-{page}-{index}"} for index in range(100)]
        return httpx.Response(200, json=items, request=request)

    async with httpx.AsyncClient(
        base_url="https://api.github.test", transport=httpx.MockTransport(handler)
    ) as http_client:
        client = GitHubApiClient(client=http_client)
        commits = await client.list_commits("owner", "repo", max_items=150)

    assert len(commits) == 150
    assert requested_pages == [1, 2]


@pytest.mark.asyncio
async def test_commit_file_pagination_reads_nested_files_list() -> None:
    requested_pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/owner/repo/commits/abc123"
        page = int(request.url.params["page"])
        requested_pages.append(page)
        files = [
            {"sha": f"sha-{page}-{index}", "filename": f"file-{page}-{index}.py"}
            for index in range(100)
        ]
        return httpx.Response(200, json={"sha": "abc123", "files": files}, request=request)

    async with httpx.AsyncClient(
        base_url="https://api.github.test", transport=httpx.MockTransport(handler)
    ) as http_client:
        client = GitHubApiClient(client=http_client)
        files = await client.list_commit_files(
            "owner", "repo", commit_sha="abc123", max_items=150
        )

    assert len(files) == 150
    assert requested_pages == [1, 2]


@pytest.mark.asyncio
async def test_rate_limit_error_contains_reset_timestamp() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1785900000"},
            request=request,
        )

    async with httpx.AsyncClient(
        base_url="https://api.github.test", transport=httpx.MockTransport(handler)
    ) as http_client:
        client = GitHubApiClient(client=http_client)
        with pytest.raises(GitHubRateLimitError, match="1785900000"):
            await client.get_repository("owner", "repo")
