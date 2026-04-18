"""seq unique constraints + FK indexes

Revision ID: 5f3a9b1c2d4e
Revises: 1a2c34090472
Create Date: 2026-04-18 10:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5f3a9b1c2d4e'
down_revision: str | Sequence[str] | None = '1a2c34090472'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # C1: unique (kindred_id, seq) on audit_log and events.
    # Use batch_alter_table so this migration is portable to SQLite (batch copy-
    # and-move strategy); Postgres executes it as a plain ALTER TABLE ADD CONSTRAINT.
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.create_unique_constraint(
            "audit_log_kindred_seq_uq", ["kindred_id", "seq"]
        )
    with op.batch_alter_table("events") as batch_op:
        batch_op.create_unique_constraint(
            "events_kindred_seq_uq", ["kindred_id", "seq"]
        )

    # C3: indexes for hot query paths and FK lookups.
    op.create_index("ix_artifacts_kindred_id", "artifacts", ["kindred_id"])
    op.create_index("ix_blessings_artifact_id", "blessings", ["artifact_id"])
    op.create_index("ix_memberships_agent_id", "memberships", ["agent_id"])
    op.create_index("ix_memberships_kindred_id", "memberships", ["kindred_id"])
    op.create_index("ix_audit_log_kindred_seq", "audit_log", ["kindred_id", "seq"])
    op.create_index("ix_events_kindred_seq", "events", ["kindred_id", "seq"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_events_kindred_seq", table_name="events")
    op.drop_index("ix_audit_log_kindred_seq", table_name="audit_log")
    op.drop_index("ix_memberships_kindred_id", table_name="memberships")
    op.drop_index("ix_memberships_agent_id", table_name="memberships")
    op.drop_index("ix_blessings_artifact_id", table_name="blessings")
    op.drop_index("ix_artifacts_kindred_id", table_name="artifacts")

    with op.batch_alter_table("events") as batch_op:
        batch_op.drop_constraint("events_kindred_seq_uq", type_="unique")
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.drop_constraint("audit_log_kindred_seq_uq", type_="unique")
