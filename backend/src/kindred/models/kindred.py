# src/kindred/models/kindred.py
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from kindred.models.base import Base, TimestampMixin


class Kindred(Base, TimestampMixin):
    __tablename__ = "kindreds"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), default="")
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    bless_threshold: Mapped[int] = mapped_column(Integer, default=2)
