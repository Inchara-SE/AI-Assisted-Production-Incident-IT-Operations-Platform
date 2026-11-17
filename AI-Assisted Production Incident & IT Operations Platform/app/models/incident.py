"""Incident model in ops schema."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.alert_event import AlertEvent
    from app.models.incident_transition import IncidentTransition
    from app.models.recommendation import Recommendation
    from app.models.service import Service


class Incident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Operational incident grouping correlated alert events."""
    __tablename__ = "incidents"

    incident_key: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    service_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.services.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    fingerprint_version: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")

    first_alert_occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    last_alert_occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    first_acknowledged_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    first_resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    reopen_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    service: Mapped[Service] = relationship("Service", back_populates="incidents")
    alert_events: Mapped[list[AlertEvent]] = relationship(
        "AlertEvent",
        back_populates="incident",
        order_by="AlertEvent.occurred_at",
    )
    transitions: Mapped[list[IncidentTransition]] = relationship(
        "IncidentTransition",
        back_populates="incident",
        order_by="IncidentTransition.occurred_at",
    )
    recommendations: Mapped[list[Recommendation]] = relationship(
        "Recommendation",
        back_populates="incident",
        order_by="Recommendation.generated_at.desc()",
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name="ck_ops_incidents_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'acknowledged', 'investigating', 'resolved')",
            name="ck_ops_incidents_status",
        ),
        CheckConstraint("reopen_count >= 0", name="ck_ops_incidents_reopen_count"),
        Index("ix_ops_incidents_status_created", "status", "created_at"),
        Index(
            "ix_ops_incidents_svc_fp_last_alert",
            "service_id",
            "normalized_fingerprint",
            "last_alert_occurred_at",
        ),
    )
