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
    parent_number = _issue_number_from_url(comment.get("issue_url"))
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
    serialized = json.dumps(hash_payload, sort_keys=True, ensure_ascii=False, default=str)
    content_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

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
        content_hash=content_hash,
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _nested_value(data: dict[str, Any], *path: str) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _issue_number_from_url(issue_url: Any) -> int | None:
    if not isinstance(issue_url, str):
        return None

    number_text = issue_url.rstrip("/").rsplit("/", maxsplit=1)[-1]
    return int(number_text) if number_text.isdigit() else None
