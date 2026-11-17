"""AuditEvent model in ops schema."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class AuditEvent(Base, UUIDPrimaryKeyMixin):
    """Append-only audit trail for operational decisions, status changes, and configurations.
    
    The application database role has INSERT and SELECT only on this table (no UPDATE or DELETE).
    """
    __tablename__ = "audit_events"

    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    actor_user: Mapped[User | None] = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "actor_type IN ('user', 'system')",
            name="ck_ops_audit_events_actor_type",
        ),
        Index("ix_ops_audit_events_entity", "entity_type", "entity_id", "occurred_at"),
    )
