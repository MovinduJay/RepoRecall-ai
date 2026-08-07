from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SemanticSearchRequest(BaseModel):
    repository_id: uuid.UUID
    query: str = Field(min_length=1, max_length=10_000)
    limit: int = Field(default=10, ge=1, le=50)
    minimum_score: float | None = Field(default=None, ge=-1.0, le=1.0)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        cleaned_query = value.strip()
        if not cleaned_query:
            raise ValueError("Query cannot be empty")
        return cleaned_query


class SemanticSearchResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    score: float
    raw_document_id: str
    repository_id: str
    source_type: str
    source_id: str
    source_number: int | None
    title: str
    text: str
    html_url: str
    chunk_index: int


class SemanticSearchResponse(BaseModel):
    query: str
    results: list[SemanticSearchResultRead]
