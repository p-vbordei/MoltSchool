# src/kindred/models/artifact.py
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from kindred.models.base import Base, TimestampMixin


class Artifact(Base, TimestampMixin):
    __tablename__ = "artifacts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    content_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    kindred_id: Mapped[UUID] = mapped_column(ForeignKey("kindreds.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    logical_name: Mapped[str] = mapped_column(String(128), nullable=False)
    author_pubkey: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    author_sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    outcome_uses: Mapped[int] = mapped_column(Integer, default=0)
    outcome_successes: Mapped[int] = mapped_column(Integer, default=0)
    superseded_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("artifacts.id"), nullable=True
    )


class Blessing(Base, TimestampMixin):
    __tablename__ = "blessings"
    __table_args__ = (UniqueConstraint("artifact_id", "signer_pubkey", name="blessing_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    artifact_id: Mapped[UUID] = mapped_column(ForeignKey("artifacts.id"), nullable=False)
    signer_pubkey: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    signer_agent_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id"), nullable=False)
    sig: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
