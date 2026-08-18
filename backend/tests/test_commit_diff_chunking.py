from app.ingestion.normalizers import CommitFileInput
from app.retrieval.commit_diff_chunking import chunk_commit_file


def test_chunk_commit_file_splits_hunks_and_keeps_commit_metadata() -> None:
    chunks = chunk_commit_file(_file_input())

    assert len(chunks) == 2
    assert chunks[0].commit_sha == "commit123"
    assert chunks[0].file_path == "app/consumer.py"
    assert chunks[0].metadata["hunk_header"].startswith("@@ -1")
    assert "+new" in chunks[0].text
    assert chunks[1].hunk_index == 1


def _file_input() -> CommitFileInput:
    return CommitFileInput(
        commit_sha="commit123",
        file_path="app/consumer.py",
        status="modified",
        file_sha="blob456",
        previous_file_path=None,
        additions=2,
        deletions=2,
        changes=4,
        patch="@@ -1 +1 @@\n-old\n+new\n@@ -10 +10 @@\n-before\n+after",
        blob_url="https://github.com/acme/billing/blob/commit123/app/consumer.py",
        raw_url="https://github.com/acme/billing/raw/commit123/app/consumer.py",
        contents_url="https://api.github.com/repos/acme/billing/contents/app/consumer.py",
        content_hash="a" * 64,
    )
