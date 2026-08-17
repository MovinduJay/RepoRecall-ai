from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.indexing_job import IndexingJob
from app.schemas.indexing_job import IndexingJobRead

router = APIRouter(prefix="/indexing-jobs", tags=["indexing jobs"])


@router.get("/{job_id}", response_model=IndexingJobRead)
async def get_indexing_job(
    job_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IndexingJob:
    job = await session.get(IndexingJob, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Indexing job was not found",
        )
    return job
