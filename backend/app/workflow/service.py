from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.generation.ollama_provider import OllamaAnswerProvider
from app.generation.openai_provider import OpenAIAnswerProvider
from app.generation.provider import AnswerProvider
from app.workflow.graph import build_investigation_graph
from app.workflow.state import InvestigationState, create_initial_state


async def run_investigation(
    repository_id: uuid.UUID,
    query: str,
) -> InvestigationState:
    """Execute the bounded historical-evidence investigation workflow."""

    initial_state = create_initial_state(query, str(repository_id))
    result = await _get_investigation_graph().ainvoke(initial_state)
    return InvestigationState(**result)


@lru_cache(maxsize=1)
def _get_investigation_graph() -> Any:
    return build_investigation_graph(answer_provider=_get_answer_provider())


@lru_cache(maxsize=1)
def _get_answer_provider() -> AnswerProvider | None:
    if settings.openai_api_key:
        return OpenAIAnswerProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
    if settings.ollama_base_url:
        return OllamaAnswerProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
    return None
