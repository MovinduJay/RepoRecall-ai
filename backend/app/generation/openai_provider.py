from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.generation.provider import GeneratedAnswer, GenerationRequest

MAX_EVIDENCE_CHARACTERS = 6_000


class StructuredGeneratedAnswer(BaseModel):
    answer: str = Field(min_length=1)
    citations: list[str]


class OpenAIAnswerProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gpt-5-nano",
        client: Any | None = None,
    ) -> None:
        if client is None and not api_key:
            raise ValueError("OPENAI_API_KEY is required for answer generation.")
        self._client = client or AsyncOpenAI(api_key=api_key)
        self._model = model

    async def generate(self, request: GenerationRequest) -> GeneratedAnswer:
        response = await self._client.responses.parse(
            model=self._model,
            instructions=request.system_instruction,
            input=_build_user_input(request),
            text_format=StructuredGeneratedAnswer,
            reasoning={"effort": "minimal"},
            store=False,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("OpenAI response did not contain a structured answer.")
        return GeneratedAnswer(
            answer=parsed.answer,
            citations=parsed.citations,
        )


def _build_user_input(request: GenerationRequest) -> str:
    evidence = [
        {
            **asdict(block),
            "text": block.text[:MAX_EVIDENCE_CHARACTERS],
        }
        for block in request.evidence
    ]
    return (
        "<developer_query>\n"
        f"{request.query}\n"
        "</developer_query>\n\n"
        "<repository_evidence_json>\n"
        f"{json.dumps(evidence, ensure_ascii=False)}\n"
        "</repository_evidence_json>"
    )
