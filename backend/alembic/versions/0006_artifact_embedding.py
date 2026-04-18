"""artifact embedding column (JSON, cross-dialect)

Revision ID: 7c4e8f2a1b9d
Revises: 5f3a9b1c2d4e
Create Date: 2026-04-18 11:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7c4e8f2a1b9d'
down_revision: str | Sequence[str] | None = '5f3a9b1c2d4e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Stored as JSON for cross-dialect portability (sqlite + postgres). At <1000
    # artefacte per kindred, Python cosine similarity is acceptable. Swap to
    # pgvector HNSW when corpus outgrows this.
    op.add_column(
        "artifacts",
        sa.Column("embedding", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("artifacts", "embedding")
