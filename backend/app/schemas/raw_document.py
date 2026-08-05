from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RawDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    source_type: str
    source_id: str
    source_number: int | None
    title: str
    body: str
    html_url: str
    author: str | None
    state: str | None
    document_metadata: dict[str, Any]
    content_hash: str
    github_created_at: datetime | None
    github_updated_at: datetime | None
    ingested_at: datetime
