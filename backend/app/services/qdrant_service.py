from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from qdrant_client import AsyncQdrantClient


class QdrantService:
    def __init__(self) -> None:
        self._client: AsyncQdrantClient | None = None

    def _get_client(self) -> AsyncQdrantClient:
        if self._client is None:
            from qdrant_client import AsyncQdrantClient

            self._client = AsyncQdrantClient(url=settings.qdrant_url, timeout=5.0)
        return self._client

    async def is_healthy(self) -> bool:
        try:
            await self._get_client().get_collections()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


qdrant_service = QdrantService()
