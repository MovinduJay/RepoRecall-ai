"""create pull request files

Revision ID: 20260817_0003
Revises: 20260805_0002
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260817_0003"
down_revision: str | None = "20260805_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pull_request_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pull_request_number", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("previous_file_path", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("sha", sa.String(length=64), nullable=False),
        sa.Column("additions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deletions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("changes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("patch", sa.Text(), nullable=True),
        sa.Column("blob_url", sa.String(length=1000), nullable=False),
        sa.Column("raw_url", sa.String(length=1000), nullable=False),
        sa.Column("contents_url", sa.String(length=1000), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "repository_id",
            "pull_request_number",
            "file_path",
            name="uq_pull_request_file_repository_pr_path",
        ),
    )
    op.create_index(
        "ix_pull_request_files_repository_id", "pull_request_files", ["repository_id"]
    )
    op.create_index(
        "ix_pull_request_files_pull_request_number",
        "pull_request_files",
        ["pull_request_number"],
    )
    op.create_index(
        "ix_pull_request_files_content_hash", "pull_request_files", ["content_hash"]
    )


def downgrade() -> None:
    op.drop_index("ix_pull_request_files_content_hash", table_name="pull_request_files")
    op.drop_index("ix_pull_request_files_pull_request_number", table_name="pull_request_files")
    op.drop_index("ix_pull_request_files_repository_id", table_name="pull_request_files")
    op.drop_table("pull_request_files")
