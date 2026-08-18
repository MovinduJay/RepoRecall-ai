from __future__ import annotations

import json
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class EvidenceReference(BaseModel):
    source_type: str = Field(min_length=1, max_length=50)
    source_id: str = Field(min_length=1, max_length=100)

    @field_validator("source_type", "source_id")
    @classmethod
    def strip_non_empty_value(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank.")
        return cleaned

    @property
    def canonical_id(self) -> str:
        return f"{self.source_type}:{self.source_id}"


class EvaluationCase(BaseModel):
    case_id: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=10_000)
    relevant_evidence: list[EvidenceReference] = Field(min_length=1)
    notes: str | None = None

    @field_validator("case_id", "query")
    @classmethod
    def strip_non_empty_value(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank.")
        return cleaned

    @model_validator(mode="after")
    def reject_duplicate_evidence(self) -> Self:
        evidence_ids = [item.canonical_id for item in self.relevant_evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Relevant evidence references must be unique within a case.")
        return self

    @property
    def relevant_ids(self) -> set[str]:
        return {item.canonical_id for item in self.relevant_evidence}


class EvaluationDataset(BaseModel):
    version: int = Field(default=1, ge=1)
    repository: str = Field(min_length=1)
    cases: list[EvaluationCase] = Field(min_length=1)

    @field_validator("repository")
    @classmethod
    def strip_repository(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Repository cannot be blank.")
        return cleaned

    @model_validator(mode="after")
    def reject_duplicate_case_ids(self) -> Self:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Evaluation case IDs must be unique.")
        return self


def load_evaluation_dataset(path: Path) -> EvaluationDataset:
    """Load and validate a versioned retrieval evaluation dataset from JSON."""

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Could not read evaluation dataset: {path}") from error

    try:
        raw_dataset = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(f"Evaluation dataset is not valid JSON: {path}") from error

    return EvaluationDataset.model_validate(raw_dataset)
