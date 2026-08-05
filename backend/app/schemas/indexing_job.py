from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RepositorySyncRequest(BaseModel):
    max_items_per_source: int | None = Field(default=None, ge=1, le=500)


class IndexingJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    status: str
    max_items_per_source: int
    issues_processed: int
    pull_requests_processed: int
    commits_processed: int
    documents_upserted: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
