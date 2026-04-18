# src/kindred/models/audit.py
from uuid import UUID, uuid4

from sqlalchemy import JSON, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from kindred.models.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kindred_id: Mapped[UUID] = mapped_column(ForeignKey("kindreds.id"), nullable=False)
    agent_pubkey: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    facilitator_sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
