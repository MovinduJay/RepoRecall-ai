from typing import Literal

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.qdrant_service import qdrant_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def readiness(
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Literal["ok", "unavailable"]]:
    postgres_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        postgres_ok = False

    qdrant_ok = await qdrant_service.is_healthy()
    if not (postgres_ok and qdrant_ok):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "postgres": "ok" if postgres_ok else "unavailable",
        "qdrant": "ok" if qdrant_ok else "unavailable",
    }
