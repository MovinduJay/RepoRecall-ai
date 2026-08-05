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
