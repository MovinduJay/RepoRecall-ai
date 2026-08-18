"""create commit files

Revision ID: 20260818_0004
Revises: 20260817_0003
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260818_0004"
down_revision: str | None = "20260817_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "commit_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("file_sha", sa.String(length=64), nullable=False),
        sa.Column("previous_file_path", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
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
            "commit_sha",
            "file_path",
            name="uq_commit_file_repository_commit_path",
        ),
    )
    op.create_index("ix_commit_files_repository_id", "commit_files", ["repository_id"])
    op.create_index("ix_commit_files_commit_sha", "commit_files", ["commit_sha"])
    op.create_index("ix_commit_files_content_hash", "commit_files", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_commit_files_content_hash", table_name="commit_files")
    op.drop_index("ix_commit_files_commit_sha", table_name="commit_files")
    op.drop_index("ix_commit_files_repository_id", table_name="commit_files")
    op.drop_table("commit_files")
