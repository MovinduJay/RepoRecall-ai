from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.raw_document import RawDocument
from app.schemas.raw_document import RawDocumentRead

router = APIRouter(prefix="/repositories", tags=["raw documents"])


@router.get("/{repository_id}/documents", response_model=list[RawDocumentRead])
async def list_raw_documents(
    repository_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    source_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[RawDocument]:
    statement = (
        select(RawDocument)
        .where(RawDocument.repository_id == repository_id)
        .order_by(RawDocument.github_updated_at.desc().nullslast())
        .limit(limit)
    )
    if source_type:
        statement = statement.where(RawDocument.source_type == source_type)

    result = await session.execute(statement)
    return list(result.scalars().all())
