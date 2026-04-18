# src/kindred/models/invite.py
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from kindred.models.base import Base, TimestampMixin


class Invite(Base, TimestampMixin):
    __tablename__ = "invites"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kindred_id: Mapped[UUID] = mapped_column(ForeignKey("kindreds.id"), nullable=False)
    issued_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    issuer_sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
