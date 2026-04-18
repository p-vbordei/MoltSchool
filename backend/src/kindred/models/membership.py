# src/kindred/models/membership.py
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, LargeBinary, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from kindred.models.base import Base, TimestampMixin


class AgentKindredMembership(Base, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("agent_id", "kindred_id", name="membership_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id"), nullable=False)
    kindred_id: Mapped[UUID] = mapped_column(ForeignKey("kindreds.id"), nullable=False)
    invite_sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    accept_sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
