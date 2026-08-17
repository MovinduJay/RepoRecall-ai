from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.models.indexing_job import IndexingJob
from app.models.repository import Repository
from app.schemas.indexing_job import IndexingJobRead, RepositorySyncRequest
from app.schemas.repository import RepositoryCreate, RepositoryRead

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post("", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
async def create_repository(
    payload: RepositoryCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Repository:
    owner, name = payload.owner_and_name()
    repository = Repository(
        owner=owner,
        name=name,
        github_url=payload.github_url,
        default_branch=payload.default_branch,
    )
    session.add(repository)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository has already been registered",
        ) from exc

    await session.refresh(repository)
    return repository


@router.get("", response_model=list[RepositoryRead])
async def list_repositories(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[Repository]:
    result = await session.execute(select(Repository).order_by(Repository.created_at.desc()))
    return list(result.scalars().all())


@router.post(
    "/{repository_id}/sync",
    response_model=IndexingJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_repository_sync(
    repository_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    payload: RepositorySyncRequest | None = None,
) -> IndexingJob:
    repository = await session.get(Repository, repository_id)
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository was not found",
        )

    active_job_result = await session.execute(
        select(IndexingJob.id).where(
            IndexingJob.repository_id == repository_id,
            IndexingJob.status.in_(["pending", "running"]),
        )
    )
    if active_job_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository already has an active indexing job",
        )

    requested_limit = payload.max_items_per_source if payload else None
    job = IndexingJob(
        repository_id=repository_id,
        max_items_per_source=requested_limit or settings.github_max_items_per_source,
    )
    repository.indexing_status = "queued"
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job
