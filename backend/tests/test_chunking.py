import uuid
from types import SimpleNamespace

from app.retrieval.chunking import chunk_raw_document


def test_chunk_raw_document_creates_multiple_chunks() -> None:
    document = SimpleNamespace(
        id=uuid.uuid4(),
        repository_id=uuid.uuid4(),
        source_type="issue",
        source_id="123",
        source_number=123,
        title="Duplicate invoice processing",
        body=(
            "The invoice is created twice after RabbitMQ reconnects.\n\n"
            "The consumer may receive the same message more than once.\n\n"
            "An idempotency check should prevent duplicate processing."
        ),
        html_url="https://github.com/example/repository/issues/123",
        author="developer",
        state="closed",
    )

    chunks = chunk_raw_document(
        document=document,
        max_characters=90,
    )

    assert len(chunks) > 1
    assert chunks[0].chunk_index == 0
    assert "Duplicate invoice processing" in chunks[0].text
    assert chunks[0].metadata["source_type"] == "issue"
    assert chunks[0].metadata["source_number"] == 123