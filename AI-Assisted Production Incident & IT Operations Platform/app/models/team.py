"""Team model in ops schema."""

from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.service import Service
    from app.models.user import User


class Team(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an engineering/operations team owning services."""
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    users: Mapped[list[User]] = relationship("User", back_populates="team", cascade="save-update, merge")
    services: Mapped[list[Service]] = relationship("Service", back_populates="owner_team", cascade="save-update, merge")
