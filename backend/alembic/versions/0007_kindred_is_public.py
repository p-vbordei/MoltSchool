"""kindred.is_public flag for one-line install

Revision ID: 9e8d7c6b5a42
Revises: 7c4e8f2a1b9d
Create Date: 2026-04-23 14:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9e8d7c6b5a42'
down_revision: str | Sequence[str] | None = '7c4e8f2a1b9d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Default false so existing kindreds stay closed; owners opt in per-kindred.
    op.add_column(
        "kindreds",
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("kindreds", "is_public")
