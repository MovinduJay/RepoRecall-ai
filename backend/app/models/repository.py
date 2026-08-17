from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.indexing_job import IndexingJob
    from app.models.pull_request_file import PullRequestFile
    from app.models.raw_document import RawDocument


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("owner", "name", name="uq_repository_owner_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    github_url: Mapped[str] = mapped_column(String(500), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    indexing_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    latest_indexed_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    indexing_jobs: Mapped[list[IndexingJob]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    raw_documents: Mapped[list[RawDocument]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    pull_request_files: Mapped[list[PullRequestFile]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
