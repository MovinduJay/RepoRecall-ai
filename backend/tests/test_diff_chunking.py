from app.ingestion.normalizers import PullRequestFileInput
from app.retrieval.diff_chunking import chunk_pull_request_file


def test_chunk_pull_request_file_splits_unified_diff_hunks() -> None:
    file_input = _file_input(
        patch=(
            "@@ -10,2 +10,3 @@ def process():\n"
            "-    acknowledge()\n"
            "+    commit()\n"
            "+    acknowledge()\n"
            "@@ -30,2 +31,3 @@ def retry():\n"
            "     process()\n"
            "+    record_attempt()"
        )
    )

    chunks = chunk_pull_request_file(file_input)

    assert len(chunks) == 2
    assert chunks[0].hunk_index == 0
    assert chunks[0].file_path == "app/consumer.py"
    assert "-    acknowledge()" in chunks[0].text
    assert "+    commit()" in chunks[0].text
    assert chunks[0].metadata["hunk_header"].startswith("@@ -10")
    assert chunks[1].hunk_index == 1
    assert "+    record_attempt()" in chunks[1].text


def test_chunk_pull_request_file_returns_no_chunks_without_patch() -> None:
    assert chunk_pull_request_file(_file_input(patch=None)) == []


def _file_input(patch: str | None) -> PullRequestFileInput:
    return PullRequestFileInput(
        pull_request_number=14,
        file_path="app/consumer.py",
        status="modified",
        sha="abc123",
        previous_file_path=None,
        additions=3,
        deletions=1,
        changes=4,
        patch=patch,
        blob_url="https://github.com/acme/billing/blob/abc123/app/consumer.py",
        raw_url="https://github.com/acme/billing/raw/abc123/app/consumer.py",
        contents_url="https://api.github.com/repos/acme/billing/contents/app/consumer.py",
        content_hash="a" * 64,
    )
