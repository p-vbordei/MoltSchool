# src/kindred/models/agent.py
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from kindred.models.base import Base, TimestampMixin


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    pubkey: Mapped[bytes] = mapped_column(LargeBinary, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    attestation_sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    attestation_scope: Mapped[str] = mapped_column(String, nullable=False)
    attestation_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
