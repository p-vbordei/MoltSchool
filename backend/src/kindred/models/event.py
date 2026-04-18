# src/kindred/models/event.py
from uuid import UUID, uuid4

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from kindred.models.base import Base, TimestampMixin


class Event(Base, TimestampMixin):
    """Write-ahead log for rollback — every state change emits an Event."""

    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kindred_id: Mapped[UUID] = mapped_column(ForeignKey("kindreds.id"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
