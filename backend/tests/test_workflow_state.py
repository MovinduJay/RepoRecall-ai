import pytest

from app.workflow.state import create_initial_state


def test_create_initial_state_normalizes_required_fields() -> None:
    state = create_initial_state("  database timeout  ", "  repository-id  ")

    assert state["query"] == "database timeout"
    assert state["repository_id"] == "repository-id"
    assert state["retry_count"] == 0
    assert state["retrieved_results"] == []
    assert state["answer"] is None


def test_create_initial_state_rejects_blank_required_fields() -> None:
    with pytest.raises(ValueError, match="Query"):
        create_initial_state("   ", "repository-id")
    with pytest.raises(ValueError, match="Repository"):
        create_initial_state("timeout", "   ")
