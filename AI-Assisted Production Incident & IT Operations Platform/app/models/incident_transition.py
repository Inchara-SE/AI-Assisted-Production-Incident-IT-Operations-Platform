"""IncidentTransition model in ops schema."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.user import User


class IncidentTransition(Base, UUIDPrimaryKeyMixin):
    """Immutable audit transition of incident lifecycle state."""
    __tablename__ = "incident_transitions"

    incident_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.incidents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    to_status: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    occurred_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    incident: Mapped[Incident] = relationship("Incident", back_populates="transitions")
    actor_user: Mapped[User | None] = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "actor_type IN ('user', 'system')",
            name="ck_ops_incident_transitions_actor_type",
        ),
        CheckConstraint(
            "to_status IN ('open', 'acknowledged', 'investigating', 'resolved')",
            name="ck_ops_incident_transitions_to_status",
        ),
        Index("ix_ops_incident_transitions_incident_occurred", "incident_id", "occurred_at"),
    )
