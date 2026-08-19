from app.workflow.query_understanding import understand_query
from app.workflow.state import create_initial_state


def test_understand_query_extracts_errors_and_normalized_paths() -> None:
    state = create_initial_state(
        "AlreadyClosedException in app\\consumers\\invoice.py followed by "
        "sqlalchemy.exc.TimeoutError from app/db/session.py. "
        "AlreadyClosedException happened twice.",
        "repository-id",
    )

    updates = understand_query(state)

    assert updates["extracted_errors"] == [
        "AlreadyClosedException",
        "sqlalchemy.exc.TimeoutError",
    ]
    assert updates["extracted_paths"] == [
        "app/consumers/invoice.py",
        "app/db/session.py",
    ]


def test_understand_query_preserves_existing_filters_and_handles_plain_prose() -> None:
    state = create_initial_state("Messages are processed twice.", "repository-id")
    state["metadata_filters"] = {"source_type": ["issue", "pull_request"]}

    updates = understand_query(state)

    assert updates == {
        "extracted_errors": [],
        "extracted_paths": [],
        "metadata_filters": {"source_type": ["issue", "pull_request"]},
    }
