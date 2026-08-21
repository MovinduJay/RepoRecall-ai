from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EvidenceBlock:
    evidence_id: str
    title: str
    text: str
    url: str


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    system_instruction: str
    query: str
    evidence: list[EvidenceBlock]


@dataclass(frozen=True, slots=True)
class GeneratedAnswer:
    answer: str
    citations: list[str]


class AnswerProvider(Protocol):
    async def generate(self, request: GenerationRequest) -> GeneratedAnswer: ...
