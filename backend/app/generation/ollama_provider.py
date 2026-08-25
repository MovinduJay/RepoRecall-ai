from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.generation.provider import GeneratedAnswer, GenerationRequest

MAX_EVIDENCE_CHARACTERS = 6_000


class StructuredGeneratedAnswer(BaseModel):
    answer: str = Field(min_length=1)
    citations: list[str]


class OllamaAnswerProvider:
    """Generate structured, evidence-grounded answers with a local Ollama server."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str = "qwen2.5:3b",
        client: Any | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("OLLAMA_BASE_URL is required for local answer generation.")
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=120.0,
        )
        self._model = model

    async def generate(self, request: GenerationRequest) -> GeneratedAnswer:
        response = await self._client.post(
            "/api/chat",
            json={
                "model": self._model,
                "stream": False,
                "format": StructuredGeneratedAnswer.model_json_schema(),
                "messages": [
                    {"role": "system", "content": request.system_instruction},
                    {"role": "user", "content": _build_user_input(request)},
                ],
                "options": {"temperature": 0},
            },
        )
        response.raise_for_status()
        try:
            parsed = StructuredGeneratedAnswer.model_validate_json(
                response.json()["message"]["content"]
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Ollama response did not contain a structured answer.") from exc
        return GeneratedAnswer(answer=parsed.answer, citations=parsed.citations)


def _build_user_input(request: GenerationRequest) -> str:
    evidence = [
        {**asdict(block), "text": block.text[:MAX_EVIDENCE_CHARACTERS]}
        for block in request.evidence
    ]
    return (
        "Answer the developer query using only the repository evidence below. "
        "Return JSON matching the requested schema.\n\n"
        f"<developer_query>\n{request.query}\n</developer_query>\n\n"
        "<repository_evidence_json>\n"
        f"{json.dumps(evidence, ensure_ascii=False)}\n"
        "</repository_evidence_json>"
    )
