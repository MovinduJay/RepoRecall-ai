from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ingestion.normalizers import PullRequestFileInput


@dataclass(frozen=True, slots=True)
class DiffChunk:
    pull_request_number: int
    file_path: str
    hunk_index: int
    text: str
    metadata: dict[str, Any]


def chunk_pull_request_file(file_input: PullRequestFileInput) -> list[DiffChunk]:
    """Split a GitHub patch at unified-diff hunk boundaries."""

    if not file_input.patch:
        return []

    hunks = split_diff_hunks(file_input.patch)

    return [
        _create_diff_chunk(file_input=file_input, hunk_lines=hunk, hunk_index=index)
        for index, hunk in enumerate(hunks)
    ]


def split_diff_hunks(patch: str) -> list[list[str]]:
    hunks: list[list[str]] = []
    current_hunk: list[str] = []

    for line in patch.splitlines():
        if line.startswith("@@ "):
            if current_hunk:
                hunks.append(current_hunk)
            current_hunk = [line]
        elif current_hunk:
            current_hunk.append(line)

    if current_hunk:
        hunks.append(current_hunk)

    return hunks


def _create_diff_chunk(
    *,
    file_input: PullRequestFileInput,
    hunk_lines: list[str],
    hunk_index: int,
) -> DiffChunk:
    hunk_header = hunk_lines[0]
    diff_text = "\n".join(hunk_lines)
    text = "\n\n".join(
        [
            f"Pull request: #{file_input.pull_request_number}",
            f"File: {file_input.file_path}",
            f"Diff:\n{diff_text}",
        ]
    )

    return DiffChunk(
        pull_request_number=file_input.pull_request_number,
        file_path=file_input.file_path,
        hunk_index=hunk_index,
        text=text,
        metadata={
            "pull_request_number": file_input.pull_request_number,
            "file_path": file_input.file_path,
            "previous_file_path": file_input.previous_file_path,
            "status": file_input.status,
            "sha": file_input.sha,
            "additions": file_input.additions,
            "deletions": file_input.deletions,
            "changes": file_input.changes,
            "hunk_header": hunk_header,
            "hunk_index": hunk_index,
            "blob_url": file_input.blob_url,
        },
    )
