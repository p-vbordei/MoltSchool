"""artifact_bodies table for in-db blob storage

Revision ID: a1b2c3d4e5f6
Revises: 9e8d7c6b5a42
Create Date: 2026-04-24 15:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | Sequence[str] | None = '9e8d7c6b5a42'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Content-addressed: content_id is SHA-256 hash, so primary key = natural dedup.
    op.create_table(
        "artifact_bodies",
        sa.Column("content_id", sa.String(length=80), primary_key=True),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("artifact_bodies")
