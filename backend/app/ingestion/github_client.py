from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings


class GitHubApiError(RuntimeError):
    """Base error raised for GitHub API failures."""


class GitHubNotFoundError(GitHubApiError):
    """Raised when a repository or resource does not exist or is inaccessible."""


class GitHubRateLimitError(GitHubApiError):
    """Raised when GitHub rejects a request because its API rate limit was reached."""


class GitHubApiClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": settings.github_api_version,
            "User-Agent": "RepoRecall-AI",
        }
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=settings.github_api_url,
            headers=headers,
            timeout=httpx.Timeout(30.0),
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_repository(self, owner: str, name: str) -> dict[str, Any]:
        response = await self._client.get(f"/repos/{owner}/{name}")
        self._raise_for_status(response)
        return response.json()

    async def list_issues(
        self, owner: str, name: str, max_items: int
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        async for page_items in self._paginate(
            f"/repos/{owner}/{name}/issues",
            params={"state": "all", "sort": "updated", "direction": "desc"},
        ):
            # GitHub's repository issues endpoint also returns pull requests.
            for item in page_items:
                if "pull_request" in item:
                    continue
                results.append(item)
                if len(results) >= max_items:
                    return results
        return results

    async def list_pull_requests(
        self, owner: str, name: str, max_items: int
    ) -> list[dict[str, Any]]:
        return await self._collect_pages(
            f"/repos/{owner}/{name}/pulls",
            params={"state": "all", "sort": "updated", "direction": "desc"},
            max_items=max_items,
        )

    async def list_commits(
        self, owner: str, name: str, max_items: int
    ) -> list[dict[str, Any]]:
        return await self._collect_pages(
            f"/repos/{owner}/{name}/commits",
            params={},
            max_items=max_items,
        )

    async def _collect_pages(
        self,
        path: str,
        params: dict[str, Any],
        max_items: int,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        async for page_items in self._paginate(path, params):
            remaining = max_items - len(results)
            if remaining <= 0:
                break
            results.extend(page_items[:remaining])
            if len(results) >= max_items:
                break

        return results

    async def _paginate(
        self, path: str, params: dict[str, Any]
    ) -> AsyncIterator[list[dict[str, Any]]]:
        page = 1
        while True:
            response = await self._client.get(
                path,
                params={**params, "per_page": 100, "page": page},
            )
            self._raise_for_status(response)
            items = response.json()
            if not isinstance(items, list):
                raise GitHubApiError("GitHub returned an unexpected paginated response")
            if not items:
                return

            yield items

            if len(items) < 100:
                return
            page += 1

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code == 404:
            raise GitHubNotFoundError("GitHub repository or resource was not found")

        if response.status_code in {403, 429}:
            remaining = response.headers.get("x-ratelimit-remaining")
            reset = response.headers.get("x-ratelimit-reset")
            if remaining == "0" or response.status_code == 429:
                detail = "GitHub API rate limit reached"
                if reset:
                    detail += f"; reset timestamp: {reset}"
                raise GitHubRateLimitError(detail)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            message = response.text[:500] or response.reason_phrase
            raise GitHubApiError(
                f"GitHub API request failed with status {response.status_code}: {message}"
            ) from exc
