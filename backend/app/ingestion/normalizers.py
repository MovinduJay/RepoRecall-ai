from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class RawDocumentInput:
    source_type: str
    source_id: str
    source_number: int | None
    title: str
    body: str
    html_url: str
    author: str | None
    state: str | None
    document_metadata: dict[str, Any]
    github_created_at: datetime | None
    github_updated_at: datetime | None
    content_hash: str


@dataclass(frozen=True, slots=True)
class PullRequestFileInput:
    pull_request_number: int
    file_path: str
    status: str
    sha: str
    previous_file_path: str | None
    additions: int
    deletions: int
    changes: int
    patch: str | None
    blob_url: str
    raw_url: str
    contents_url: str
    content_hash: str


def normalize_issue(issue: dict[str, Any]) -> RawDocumentInput:
    labels = [label.get("name") for label in issue.get("labels", []) if label.get("name")]
    return _build_document(
        source_type="issue",
        source_id=str(issue["id"]),
        source_number=issue.get("number"),
        title=issue.get("title") or f"Issue #{issue.get('number', 'unknown')}",
        body=issue.get("body") or "",
        html_url=issue["html_url"],
        author=_nested_value(issue, "user", "login"),
        state=issue.get("state"),
        document_metadata={
            "labels": labels,
            "comments_count": issue.get("comments", 0),
            "state_reason": issue.get("state_reason"),
            "locked": issue.get("locked", False),
        },
        created_at=issue.get("created_at"),
        updated_at=issue.get("updated_at"),
    )


def normalize_pull_request(pull_request: dict[str, Any]) -> RawDocumentInput:
    return _build_document(
        source_type="pull_request",
        source_id=str(pull_request["id"]),
        source_number=pull_request.get("number"),
        title=pull_request.get("title") or f"Pull request #{pull_request.get('number', 'unknown')}",
        body=pull_request.get("body") or "",
        html_url=pull_request["html_url"],
        author=_nested_value(pull_request, "user", "login"),
        state=pull_request.get("state"),
        document_metadata={
            "draft": pull_request.get("draft", False),
            "merged_at": pull_request.get("merged_at"),
            "base_ref": _nested_value(pull_request, "base", "ref"),
            "head_ref": _nested_value(pull_request, "head", "ref"),
            "head_sha": _nested_value(pull_request, "head", "sha"),
        },
        created_at=pull_request.get("created_at"),
        updated_at=pull_request.get("updated_at"),
    )


def normalize_issue_comment(comment: dict[str, Any]) -> RawDocumentInput:
    parent_number = _resource_number_from_url(comment.get("issue_url"))
    parent_label = f" #{parent_number}" if parent_number is not None else ""

    return _build_document(
        source_type="issue_comment",
        source_id=str(comment["id"]),
        source_number=None,
        title=f"Comment on issue or pull request{parent_label}",
        body=comment.get("body") or "",
        html_url=comment["html_url"],
        author=_nested_value(comment, "user", "login"),
        state=None,
        document_metadata={
            "parent_number": parent_number,
            "author_association": comment.get("author_association"),
            "minimized": comment.get("minimized", False),
        },
        created_at=comment.get("created_at"),
        updated_at=comment.get("updated_at"),
    )


def normalize_pull_request_review_comment(comment: dict[str, Any]) -> RawDocumentInput:
    pull_request_number = _resource_number_from_url(comment.get("pull_request_url"))
    number_label = f" #{pull_request_number}" if pull_request_number is not None else ""
    file_path = comment.get("path")
    path_label = f" on {file_path}" if file_path else ""

    return _build_document(
        source_type="pull_request_review_comment",
        source_id=str(comment["id"]),
        source_number=None,
        title=f"Review comment on pull request{number_label}{path_label}",
        body=comment.get("body") or "",
        html_url=comment["html_url"],
        author=_nested_value(comment, "user", "login"),
        state=None,
        document_metadata={
            "pull_request_number": pull_request_number,
            "pull_request_review_id": comment.get("pull_request_review_id"),
            "file_path": file_path,
            "diff_hunk": comment.get("diff_hunk"),
            "commit_id": comment.get("commit_id"),
            "original_commit_id": comment.get("original_commit_id"),
            "in_reply_to_id": comment.get("in_reply_to_id"),
            "start_line": comment.get("start_line"),
            "line": comment.get("line"),
            "side": comment.get("side"),
            "author_association": comment.get("author_association"),
        },
        created_at=comment.get("created_at"),
        updated_at=comment.get("updated_at"),
    )


def normalize_pull_request_file(
    pull_request_number: int,
    file_item: dict[str, Any],
) -> PullRequestFileInput:
    hash_payload = {
        "pull_request_number": pull_request_number,
        "file_path": file_item["filename"],
        "status": file_item["status"],
        "sha": file_item["sha"],
        "previous_file_path": file_item.get("previous_filename"),
        "additions": file_item.get("additions", 0),
        "deletions": file_item.get("deletions", 0),
        "changes": file_item.get("changes", 0),
        "patch": file_item.get("patch"),
    }

    return PullRequestFileInput(
        pull_request_number=pull_request_number,
        file_path=file_item["filename"],
        status=file_item["status"],
        sha=file_item["sha"],
        previous_file_path=file_item.get("previous_filename"),
        additions=file_item.get("additions", 0),
        deletions=file_item.get("deletions", 0),
        changes=file_item.get("changes", 0),
        patch=file_item.get("patch"),
        blob_url=file_item["blob_url"],
        raw_url=file_item["raw_url"],
        contents_url=file_item["contents_url"],
        content_hash=_content_hash(hash_payload),
    )


def normalize_commit(commit_item: dict[str, Any]) -> RawDocumentInput:
    commit = commit_item.get("commit") or {}
    message = commit.get("message") or ""
    title, _, remainder = message.partition("\n")
    author = _nested_value(commit_item, "author", "login") or _nested_value(
        commit, "author", "name"
    )

    return _build_document(
        source_type="commit",
        source_id=commit_item["sha"],
        source_number=None,
        title=title or f"Commit {commit_item['sha'][:7]}",
        body=remainder.strip(),
        html_url=commit_item["html_url"],
        author=author,
        state=None,
        document_metadata={
            "sha": commit_item["sha"],
            "committer": _nested_value(commit_item, "committer", "login")
            or _nested_value(commit, "committer", "name"),
            "verification_reason": _nested_value(commit, "verification", "reason"),
        },
        created_at=_nested_value(commit, "author", "date"),
        updated_at=_nested_value(commit, "committer", "date"),
    )


def _build_document(
    *,
    source_type: str,
    source_id: str,
    source_number: int | None,
    title: str,
    body: str,
    html_url: str,
    author: str | None,
    state: str | None,
    document_metadata: dict[str, Any],
    created_at: str | None,
    updated_at: str | None,
) -> RawDocumentInput:
    hash_payload = {
        "source_type": source_type,
        "source_id": source_id,
        "title": title,
        "body": body,
        "metadata": document_metadata,
    }
    return RawDocumentInput(
        source_type=source_type,
        source_id=source_id,
        source_number=source_number,
        title=title,
        body=body,
        html_url=html_url,
        author=author,
        state=state,
        document_metadata=document_metadata,
        github_created_at=_parse_datetime(created_at),
        github_updated_at=_parse_datetime(updated_at),
        content_hash=_content_hash(hash_payload),
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _content_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _nested_value(data: dict[str, Any], *path: str) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _resource_number_from_url(resource_url: Any) -> int | None:
    if not isinstance(resource_url, str):
        return None

    number_text = resource_url.rstrip("/").rsplit("/", maxsplit=1)[-1]
    return int(number_text) if number_text.isdigit() else None
