"""User model in ops schema."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.role import UserRole
    from app.models.team import Team


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account with email, display name, Argon2id hash, and team association."""
    __tablename__ = "users"

    team_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.teams.id", ondelete="RESTRICT"),
        nullable=True,
    )
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    team: Mapped[Team | None] = relationship("Team", back_populates="users")
    user_roles: Mapped[list[UserRole]] = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_ops_users_team_id", "team_id"),
    )

    @property
    def roles(self) -> list[str]:
        """Convenience property returning role codes."""
        return [ur.role.role_code for ur in self.user_roles if ur.role]
