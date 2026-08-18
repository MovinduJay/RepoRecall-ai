from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ingestion.normalizers import CommitFileInput
from app.retrieval.diff_chunking import split_diff_hunks


@dataclass(frozen=True, slots=True)
class CommitDiffChunk:
    commit_sha: str
    file_path: str
    hunk_index: int
    text: str
    metadata: dict[str, Any]


def chunk_commit_file(file_input: CommitFileInput) -> list[CommitDiffChunk]:
    if not file_input.patch:
        return []

    return [
        _create_commit_diff_chunk(file_input=file_input, hunk_lines=hunk, hunk_index=index)
        for index, hunk in enumerate(split_diff_hunks(file_input.patch))
    ]


def _create_commit_diff_chunk(
    *,
    file_input: CommitFileInput,
    hunk_lines: list[str],
    hunk_index: int,
) -> CommitDiffChunk:
    hunk_header = hunk_lines[0]
    diff_text = "\n".join(hunk_lines)
    text = "\n\n".join(
        [
            f"Commit: {file_input.commit_sha}",
            f"File: {file_input.file_path}",
            f"Diff:\n{diff_text}",
        ]
    )

    return CommitDiffChunk(
        commit_sha=file_input.commit_sha,
        file_path=file_input.file_path,
        hunk_index=hunk_index,
        text=text,
        metadata={
            "commit_sha": file_input.commit_sha,
            "file_path": file_input.file_path,
            "file_sha": file_input.file_sha,
            "previous_file_path": file_input.previous_file_path,
            "status": file_input.status,
            "additions": file_input.additions,
            "deletions": file_input.deletions,
            "changes": file_input.changes,
            "hunk_header": hunk_header,
            "hunk_index": hunk_index,
            "blob_url": file_input.blob_url,
        },
    )
