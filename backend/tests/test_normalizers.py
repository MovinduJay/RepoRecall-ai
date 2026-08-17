from app.ingestion.normalizers import (
    normalize_commit,
    normalize_issue,
    normalize_issue_comment,
    normalize_pull_request,
    normalize_pull_request_file,
    normalize_pull_request_review_comment,
)


def test_normalize_issue_creates_stable_searchable_record() -> None:
    issue = normalize_issue(
        {
            "id": 101,
            "number": 12,
            "title": "Duplicate invoice on redelivery",
            "body": "The same RabbitMQ message is handled twice.",
            "html_url": "https://github.com/acme/billing/issues/12",
            "user": {"login": "movindu"},
            "state": "closed",
            "labels": [{"name": "bug"}, {"name": "rabbitmq"}],
            "comments": 3,
            "created_at": "2026-07-01T10:00:00Z",
            "updated_at": "2026-07-02T10:00:00Z",
        }
    )

    assert issue.source_type == "issue"
    assert issue.source_number == 12
    assert issue.document_metadata["labels"] == ["bug", "rabbitmq"]
    assert len(issue.content_hash) == 64


def test_normalize_pull_request_keeps_branch_metadata() -> None:
    pull_request = normalize_pull_request(
        {
            "id": 201,
            "number": 14,
            "title": "Make invoice processing idempotent",
            "body": "Stores processed message IDs.",
            "html_url": "https://github.com/acme/billing/pull/14",
            "user": {"login": "dev"},
            "state": "closed",
            "draft": False,
            "merged_at": "2026-07-03T10:00:00Z",
            "base": {"ref": "main"},
            "head": {"ref": "fix/idempotency", "sha": "abc123"},
            "created_at": "2026-07-02T10:00:00Z",
            "updated_at": "2026-07-03T10:00:00Z",
        }
    )

    assert pull_request.document_metadata["base_ref"] == "main"
    assert pull_request.document_metadata["head_sha"] == "abc123"


def test_normalize_issue_comment_keeps_parent_metadata() -> None:
    comment = normalize_issue_comment(
        {
            "id": 301,
            "body": "Acknowledge the message only after the transaction commits.",
            "html_url": "https://github.com/acme/billing/issues/12#issuecomment-301",
            "issue_url": "https://api.github.com/repos/acme/billing/issues/12",
            "user": {"login": "reviewer"},
            "author_association": "COLLABORATOR",
            "created_at": "2026-07-02T11:00:00Z",
            "updated_at": "2026-07-02T12:00:00Z",
        }
    )

    assert comment.source_type == "issue_comment"
    assert comment.source_id == "301"
    assert comment.source_number is None
    assert comment.title == "Comment on issue or pull request #12"
    assert comment.document_metadata["parent_number"] == 12
    assert comment.document_metadata["author_association"] == "COLLABORATOR"
    assert len(comment.content_hash) == 64


def test_normalize_review_comment_keeps_code_location_metadata() -> None:
    comment = normalize_pull_request_review_comment(
        {
            "id": 401,
            "pull_request_review_id": 501,
            "body": "Move acknowledgement after the database transaction.",
            "html_url": "https://github.com/acme/billing/pull/14#discussion_r401",
            "pull_request_url": "https://api.github.com/repos/acme/billing/pulls/14",
            "user": {"login": "reviewer"},
            "author_association": "COLLABORATOR",
            "path": "app/consumer.py",
            "diff_hunk": "@@ -20,2 +20,2 @@\n-ack()\n commit()",
            "commit_id": "abc123",
            "original_commit_id": "def456",
            "line": 21,
            "side": "RIGHT",
            "created_at": "2026-07-02T11:00:00Z",
            "updated_at": "2026-07-02T12:00:00Z",
        }
    )

    assert comment.source_type == "pull_request_review_comment"
    assert comment.source_id == "401"
    assert comment.source_number is None
    assert comment.title == "Review comment on pull request #14 on app/consumer.py"
    assert comment.document_metadata["pull_request_number"] == 14
    assert comment.document_metadata["file_path"] == "app/consumer.py"
    assert comment.document_metadata["diff_hunk"].startswith("@@ -20")
    assert comment.document_metadata["line"] == 21
    assert len(comment.content_hash) == 64


def test_normalize_pull_request_file_keeps_patch_separate() -> None:
    file_input = normalize_pull_request_file(
        pull_request_number=14,
        file_item={
            "sha": "abc123",
            "filename": "app/consumer.py",
            "previous_filename": "app/old_consumer.py",
            "status": "renamed",
            "additions": 4,
            "deletions": 2,
            "changes": 6,
            "patch": "@@ -20,2 +20,4 @@\n-ack()\n commit()\n+commit()\n+ack()",
            "blob_url": "https://github.com/acme/billing/blob/abc123/app/consumer.py",
            "raw_url": "https://github.com/acme/billing/raw/abc123/app/consumer.py",
            "contents_url": "https://api.github.com/repos/acme/billing/contents/app/consumer.py",
        },
    )

    assert file_input.pull_request_number == 14
    assert file_input.file_path == "app/consumer.py"
    assert file_input.previous_file_path == "app/old_consumer.py"
    assert file_input.status == "renamed"
    assert file_input.changes == 6
    assert file_input.patch.startswith("@@ -20")
    assert len(file_input.content_hash) == 64


def test_normalize_commit_splits_subject_from_body() -> None:
    commit = normalize_commit(
        {
            "sha": "8f21c4a",
            "html_url": "https://github.com/acme/billing/commit/8f21c4a",
            "author": {"login": "dev"},
            "committer": {"login": "dev"},
            "commit": {
                "message": "Prevent duplicate invoice processing\n\nAcknowledge after commit.",
                "author": {"name": "Developer", "date": "2026-07-03T10:00:00Z"},
                "committer": {"name": "Developer", "date": "2026-07-03T10:01:00Z"},
                "verification": {"reason": "valid"},
            },
        }
    )

    assert commit.title == "Prevent duplicate invoice processing"
    assert commit.body == "Acknowledge after commit."
    assert commit.source_id == "8f21c4a"
