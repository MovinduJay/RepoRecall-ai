from __future__ import annotations

import uuid
from typing import Literal

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


class LexicalSearchRequest(BaseModel):
    repository_id: uuid.UUID
    query: str = Field(min_length=1, max_length=10_000)
    limit: int = Field(default=10, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        cleaned_query = value.strip()
        if not cleaned_query:
            raise ValueError("Query cannot be empty")
        return cleaned_query


class LexicalSearchResultRead(SemanticSearchResultRead):
    pass


class LexicalSearchResponse(BaseModel):
    query: str
    results: list[LexicalSearchResultRead]


class HybridSearchRequest(LexicalSearchRequest):
    pass


class HybridSearchResultRead(SemanticSearchResultRead):
    semantic_score: float | None
    lexical_score: float | None


class HybridSearchResponse(BaseModel):
    query: str
    results: list[HybridSearchResultRead]


class RerankedSearchRequest(LexicalSearchRequest):
    pass


class RerankedSearchResultRead(HybridSearchResultRead):
    rrf_score: float


class RerankedSearchResponse(BaseModel):
    query: str
    results: list[RerankedSearchResultRead]


class InvestigationRequest(LexicalSearchRequest):
    pass


class InvestigationResponse(BaseModel):
    query: str
    decision: Literal["sufficient", "rewrite", "abstain"]
    confidence: float
    retry_count: int
    extracted_errors: list[str]
    extracted_paths: list[str]
    rewritten_queries: list[str]
    evidence: list[RerankedSearchResultRead]
    answer: str | None
    citations: list[str]
    generation_error: str | None


class DiffSearchRequest(SemanticSearchRequest):
    pass


class DiffSearchResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    score: float
    repository_id: str
    pull_request_number: int
    file_path: str
    status: str
    sha: str
    hunk_header: str
    hunk_index: int
    text: str
    blob_url: str


class DiffSearchResponse(BaseModel):
    query: str
    results: list[DiffSearchResultRead]
