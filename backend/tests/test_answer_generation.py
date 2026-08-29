from unittest.mock import AsyncMock

import pytest

from app.generation.provider import GeneratedAnswer
from app.retrieval.reranker import RerankedSearchResult
from app.workflow.answer_generation import SYSTEM_INSTRUCTION, generate_answer
from app.workflow.citations import InvalidCitationError
from app.workflow.state import create_initial_state


@pytest.mark.asyncio
async def test_generate_answer_sends_untrusted_evidence_and_validates_citations() -> None:
    state = _sufficient_state()
    provider = AsyncMock()
    provider.generate.return_value = GeneratedAnswer(
        answer="  PR #10 increased the connection timeout.  ",
        citations=["https://github.com/acme/repo/pull/10"],
    )

    updates = await generate_answer(state, provider)

    assert updates == {
        "answer": "PR #10 increased the connection timeout.",
        "citations": ["https://github.com/acme/repo/pull/10"],
    }
    request = provider.generate.await_args.args[0]
    assert request.system_instruction == SYSTEM_INSTRUCTION
    assert "untrusted data" in request.system_instruction
    assert request.query == "database timeout"
    assert request.evidence[0].evidence_id == "evidence-1"
    assert request.evidence[0].url == "https://github.com/acme/repo/pull/10"


@pytest.mark.asyncio
async def test_generate_answer_rejects_invented_or_missing_citations() -> None:
    state = _sufficient_state()
    provider = AsyncMock()
    provider.generate.return_value = GeneratedAnswer(
        answer="The timeout was increased.",
        citations=["https://github.com/acme/repo/pull/999"],
    )

    with pytest.raises(InvalidCitationError, match="pull/999"):
        await generate_answer(state, provider)

    provider.generate.return_value = GeneratedAnswer(
        answer="The timeout was increased.",
        citations=[],
    )
    with pytest.raises(InvalidCitationError, match="must cite"):
        await generate_answer(state, provider)


@pytest.mark.asyncio
async def test_generate_answer_resolves_provider_evidence_identifier() -> None:
    state = _sufficient_state()
    provider = AsyncMock()
    provider.generate.return_value = GeneratedAnswer(
        answer="The timeout was increased.",
        citations=["evidence-1"],
    )

    updates = await generate_answer(state, provider)

    assert updates == {
        "answer": "The timeout was increased.",
        "citations": ["https://github.com/acme/repo/pull/10"],
    }


@pytest.mark.asyncio
async def test_generate_answer_requires_sufficient_nonempty_evidence() -> None:
    provider = AsyncMock()
    weak_state = create_initial_state("database timeout", "repository-id")
    weak_state["decision"] = "abstain"

    with pytest.raises(ValueError, match="sufficient"):
        await generate_answer(weak_state, provider)

    weak_state["decision"] = "sufficient"
    with pytest.raises(ValueError, match="without retrieved evidence"):
        await generate_answer(weak_state, provider)
    provider.generate.assert_not_awaited()


def _sufficient_state():
    state = create_initial_state("database timeout", "repository-id")
    state["decision"] = "sufficient"
    state["retrieved_results"] = [
        RerankedSearchResult(
            score=0.82,
            rrf_score=0.03,
            semantic_score=0.75,
            lexical_score=4.2,
            raw_document_id="document-1",
            repository_id="repository-1",
            source_type="pull_request",
            source_id="123456",
            source_number=10,
            title="Fix database timeout",
            text="Increase the pool timeout.",
            html_url="https://github.com/acme/repo/pull/10",
            chunk_index=0,
        )
    ]
    return state
