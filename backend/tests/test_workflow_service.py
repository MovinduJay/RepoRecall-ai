import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from app.workflow import service
from app.workflow.state import create_initial_state


@pytest.mark.asyncio
async def test_run_investigation_invokes_cached_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_id = uuid.uuid4()
    completed_state = create_initial_state("database timeout", str(repository_id))
    completed_state["decision"] = "abstain"
    workflow = AsyncMock()
    workflow.ainvoke.return_value = completed_state
    monkeypatch.setattr(service, "_get_investigation_graph", lambda: workflow)

    result = await service.run_investigation(repository_id, "  database timeout  ")

    assert result == completed_state
    invoked_state = workflow.ainvoke.await_args.args[0]
    assert invoked_state["query"] == "database timeout"
    assert invoked_state["repository_id"] == str(repository_id)


def test_answer_provider_is_optional_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service.settings, "openai_api_key", None)
    service._get_answer_provider.cache_clear()

    try:
        assert service._get_answer_provider() is None
    finally:
        service._get_answer_provider.cache_clear()


def test_answer_provider_uses_configured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = object()
    create_provider = Mock(return_value=provider)
    monkeypatch.setattr(service.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(service.settings, "openai_model", "test-model")
    monkeypatch.setattr(service, "OpenAIAnswerProvider", create_provider)
    service._get_answer_provider.cache_clear()

    try:
        assert service._get_answer_provider() is provider
        create_provider.assert_called_once_with(api_key="test-key", model="test-model")
    finally:
        service._get_answer_provider.cache_clear()
