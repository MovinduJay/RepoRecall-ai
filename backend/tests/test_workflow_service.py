import uuid
from unittest.mock import AsyncMock

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
