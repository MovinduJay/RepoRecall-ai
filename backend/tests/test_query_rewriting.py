import pytest

from app.workflow.query_rewriting import HISTORICAL_FIX_CONTEXT, rewrite_query
from app.workflow.state import create_initial_state


def test_rewrite_query_prioritizes_extracted_technical_signals() -> None:
    state = create_initial_state(
        "The consumer fails after reconnecting.",
        "repository-id",
    )
    state["extracted_errors"] = ["AlreadyClosedException"]
    state["extracted_paths"] = ["app/consumer.py"]

    updates = rewrite_query(state)

    assert updates == {
        "rewritten_queries": [
            "AlreadyClosedException app/consumer.py\n"
            "The consumer fails after reconnecting."
        ],
        "retry_count": 1,
    }


def test_rewrite_query_adds_historical_context_without_exact_signals() -> None:
    state = create_initial_state("Messages are processed twice.", "repository-id")

    updates = rewrite_query(state)

    assert updates["rewritten_queries"] == [
        f"{HISTORICAL_FIX_CONTEXT}\nMessages are processed twice."
    ]


def test_rewrite_query_preserves_history_and_refuses_second_retry() -> None:
    state = create_initial_state("database timeout", "repository-id")
    state["rewritten_queries"] = ["first rewrite"]
    state["retry_count"] = 1

    with pytest.raises(ValueError, match="Maximum"):
        rewrite_query(state)

    assert state["rewritten_queries"] == ["first rewrite"]
