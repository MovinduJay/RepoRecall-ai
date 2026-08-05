from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

GITHUB_REPOSITORY_PATTERN = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+?)/?$"
)


class RepositoryCreate(BaseModel):
    github_url: str = Field(examples=["https://github.com/fastapi/fastapi"])
    default_branch: str = "main"

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, value: str) -> str:
        cleaned = value.strip().removesuffix(".git")
        if not GITHUB_REPOSITORY_PATTERN.match(cleaned):
            raise ValueError("Provide a public GitHub repository URL")
        return cleaned

    def owner_and_name(self) -> tuple[str, str]:
        match = GITHUB_REPOSITORY_PATTERN.match(self.github_url)
        if match is None:  # Defensive; validation already guarantees this.
            raise ValueError("Invalid GitHub repository URL")
        return match.group("owner"), match.group("name")


class RepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner: str
    name: str
    github_url: str
    default_branch: str
    indexing_status: str
    latest_indexed_sha: str | None
    created_at: datetime
