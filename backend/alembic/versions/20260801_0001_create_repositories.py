"""create repositories table

Revision ID: 20260801_0001
Revises:
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260801_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("github_url", sa.String(length=500), nullable=False),
        sa.Column("default_branch", sa.String(length=100), nullable=False, server_default="main"),
        sa.Column("indexing_status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("latest_indexed_sha", sa.String(length=40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("owner", "name", name="uq_repository_owner_name"),
    )


def downgrade() -> None:
    op.drop_table("repositories")
