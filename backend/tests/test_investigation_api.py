import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.routes import search
from app.main import app
from app.retrieval.reranker import RerankedSearchResult
from app.workflow.state import create_initial_state


def test_investigation_endpoint_returns_workflow_state_and_evidence() -> None:
    repository_id = uuid.uuid4()
    state = create_initial_state("TimeoutError in app/db.py", str(repository_id))
    state.update(
        {
            "decision": "sufficient",
            "confidence": 0.82,
            "extracted_errors": ["TimeoutError"],
            "extracted_paths": ["app/db.py"],
            "retrieved_results": [_result(repository_id)],
        }
    )
    run_investigation = AsyncMock(return_value=state)
    original_run = search.run_investigation
    search.run_investigation = run_investigation

    try:
        response = TestClient(app).post(
            "/api/v1/search/investigate",
            json={
                "repository_id": str(repository_id),
                "query": "  TimeoutError in app/db.py  ",
            },
        )
    finally:
        search.run_investigation = original_run

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "sufficient"
    assert body["confidence"] == 0.82
    assert body["extracted_errors"] == ["TimeoutError"]
    assert body["evidence"][0]["source_number"] == 10
    assert body["answer"] is None
    run_investigation.assert_awaited_once_with(
        repository_id=repository_id,
        query="TimeoutError in app/db.py",
    )


def test_investigation_endpoint_rejects_blank_query() -> None:
    response = TestClient(app).post(
        "/api/v1/search/investigate",
        json={"repository_id": str(uuid.uuid4()), "query": "   "},
    )

    assert response.status_code == 422


def _result(repository_id: uuid.UUID) -> RerankedSearchResult:
    return RerankedSearchResult(
        score=0.82,
        rrf_score=0.03,
        semantic_score=0.75,
        lexical_score=4.2,
        raw_document_id=str(uuid.uuid4()),
        repository_id=str(repository_id),
        source_type="pull_request",
        source_id="123456",
        source_number=10,
        title="Fix database timeout",
        text="Increase the pool timeout.",
        html_url="https://github.com/acme/repo/pull/10",
        chunk_index=0,
    )
