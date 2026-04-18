# src/kindred/models/user.py
from uuid import UUID, uuid4

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from kindred.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    pubkey: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
