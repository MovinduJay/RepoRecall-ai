"""create indexing jobs and raw documents

Revision ID: 20260805_0002
Revises: 20260801_0001
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260805_0002"
down_revision: str | None = "20260801_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "indexing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("max_items_per_source", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("issues_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pull_requests_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("commits_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("documents_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_indexing_jobs_repository_id", "indexing_jobs", ["repository_id"])
    op.create_index("ix_indexing_jobs_status", "indexing_jobs", ["status"])

    op.create_table(
        "raw_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("source_number", sa.Integer(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("html_url", sa.String(length=1000), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=50), nullable=True),
        sa.Column(
            "document_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("github_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("github_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "repository_id",
            "source_type",
            "source_id",
            name="uq_raw_document_repository_source",
        ),
    )
    op.create_index("ix_raw_documents_repository_id", "raw_documents", ["repository_id"])
    op.create_index("ix_raw_documents_source_type", "raw_documents", ["source_type"])
    op.create_index("ix_raw_documents_content_hash", "raw_documents", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_raw_documents_content_hash", table_name="raw_documents")
    op.drop_index("ix_raw_documents_source_type", table_name="raw_documents")
    op.drop_index("ix_raw_documents_repository_id", table_name="raw_documents")
    op.drop_table("raw_documents")

    op.drop_index("ix_indexing_jobs_status", table_name="indexing_jobs")
    op.drop_index("ix_indexing_jobs_repository_id", table_name="indexing_jobs")
    op.drop_table("indexing_jobs")
