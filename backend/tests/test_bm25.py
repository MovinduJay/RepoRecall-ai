import pytest

from app.retrieval.bm25 import BM25Document, rank_bm25, tokenize


def test_tokenize_preserves_software_identifiers() -> None:
    assert tokenize("AlreadyClosedException in InvoiceConsumer.java: process_invoice") == [
        "alreadyclosedexception",
        "in",
        "invoiceconsumer.java:",
        "process_invoice",
    ]


def test_rank_bm25_prioritizes_exact_rare_terms() -> None:
    documents = [
        BM25Document(
            document_id="generic",
            text="The message consumer failed after reconnecting to the broker.",
        ),
        BM25Document(
            document_id="exact",
            text="InvoiceConsumer.java raised AlreadyClosedException after reconnecting.",
        ),
        BM25Document(
            document_id="unrelated",
            text="Update the frontend navigation colors.",
        ),
    ]

    results = rank_bm25("AlreadyClosedException InvoiceConsumer.java", documents)

    assert [result.document_id for result in results] == ["exact"]
    assert results[0].score > 0


def test_rank_bm25_applies_length_normalization() -> None:
    documents = [
        BM25Document(document_id="short", text="HTTP 409 conflict"),
        BM25Document(
            document_id="long",
            text="HTTP 409 conflict " + "unrelated context " * 30,
        ),
    ]

    results = rank_bm25("HTTP 409", documents)

    assert [result.document_id for result in results] == ["short", "long"]
    assert results[0].score > results[1].score


def test_rank_bm25_limits_results_and_rejects_blank_query() -> None:
    documents = [
        BM25Document(document_id="one", text="database timeout"),
        BM25Document(document_id="two", text="database connection timeout"),
    ]

    assert len(rank_bm25("timeout", documents, limit=1)) == 1

    with pytest.raises(ValueError, match="searchable token"):
        rank_bm25("()", documents)
